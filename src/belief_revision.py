"""
MemoriaGraph 3.0 - Dynamic Belief Revision & Evidence Engine (Hindsight Pillar)
Menerapkan pembaruan keyakinan dinamis dengan Logarithmic Dampening dan Hysteresis.
Mengelola status epistemik: CANDIDATE -> OBSERVED -> HIGH_CONFIDENCE (atau CONTESTED / DEPRECATED).
"""

import datetime
from datetime import timezone
import math
import sys
import uuid
from typing import Any

from neo4j import Driver

from src.event_logger import log_raw_event


def calculate_reinforced_score(
    current_evidence: int,
    current_counter: int,
    current_score: float
) -> tuple[float, str]:
    """
    Menghitung peningkatan keyakinan berbasis penguatan positif baru.
    Menggunakan Logarithmic Dampening untuk mencegah lonjakan liar:
    Delta S = 0.35 / (1 + log2(E + 1))
    """
    new_evidence = current_evidence + 1
    # Logarithmic dampening
    delta = 0.35 / (1.0 + math.log2(new_evidence + 1))
    new_score = round(min(0.99, current_score + delta), 4)

    # Penentuan status
    if new_score >= 0.90 and new_evidence >= 4 and current_counter <= 1:
        new_status = "HIGH_CONFIDENCE"
    elif new_score >= 0.65 and new_evidence >= 2 and current_counter < new_evidence:
        new_status = "OBSERVED"
    elif current_counter >= new_evidence or new_score < 0.40:
        new_status = "CONTESTED"
    else:
        new_status = "CANDIDATE"

    return new_score, new_status

def calculate_challenged_score(
    current_evidence: int,
    current_counter: int,
    current_score: float
) -> tuple[float, str]:
    """
    Menghitung penurunan keyakinan akibat fakta kegagalan (counter-evidence).
    Menerapkan Hysteresis: Keyakinan yang sudah terbukti banyak (E tinggi)
    tidak runtuh oleh kegagalan tunggal, namun tetap mengalami penalti proporsional.
    Delta S = 0.40 / sqrt(E + 1)
    """
    new_counter = current_counter + 1
    delta = 0.40 / math.sqrt(max(1, current_evidence) + 1.0)
    new_score = round(max(0.05, current_score - delta), 4)

    if new_counter >= current_evidence or new_score < 0.40:
        new_status = "CONTESTED"
    elif new_score < 0.20:
        new_status = "DEPRECATED"
    elif new_score >= 0.65 and current_evidence >= 3:
        new_status = "OBSERVED"
    else:
        new_status = "CANDIDATE"

    return new_score, new_status

def migrate_existing_beliefs(driver: Driver) -> int:
    """
    Inisialisasi properti bukti (evidence) pada semua node :Reflection dan :Pattern lama di Neo4j.
    """
    cypher = """
    MATCH (r:Reflection)
    WHERE r.confidence_score IS NULL OR r.evidence_count IS NULL
    SET r.evidence_count = coalesce(r.evidence_count, 1),
        r.counter_evidence_count = coalesce(r.counter_evidence_count, 0),
        r.confidence_score = coalesce(r.confidence_score, 0.60),
        r.status = coalesce(r.status, 'OBSERVED'),
        r.last_reinforced = coalesce(r.last_reinforced, r.timestamp, datetime())
    RETURN count(r) AS updated_count
    """
    with driver.session() as s:
        res = s.run(cypher).single()
        count = res["updated_count"] if res else 0
        
        # Juga untuk Pattern jika ada
        s.run("""
        MATCH (p:Pattern)
        WHERE p.confidence_score IS NULL OR p.evidence_count IS NULL
        SET p.evidence_count = coalesce(p.evidence_count, 1),
            p.counter_evidence_count = coalesce(p.counter_evidence_count, 0),
            p.confidence_score = coalesce(p.confidence_score, 0.65),
            p.status = coalesce(p.status, 'OBSERVED'),
            p.last_reinforced = coalesce(p.last_reinforced, datetime())
        """)
        
    print(f"✅ [BeliefRevision] Migrasi selesai: {count} node Reflection dimutakhirkan.", file=sys.stderr)
    return count

def reinforce_belief(
    driver: Driver,
    identifier: str,
    details: str = "",
    episode_id: str | None = None
) -> dict[str, Any]:
    """
    Memperkuat keyakinan / heuristik berdasarkan bukti sukses baru.
    Menerapkan logarithmic dampening dan mengkristalisasikan menjadi Pattern jika matang.
    """
    now_iso = datetime.datetime.now(timezone.utc).isoformat()
    
    with driver.session() as s:
        # Cari node Reflection atau Pattern berdasarkan ID atau kemiripan teks
        find_query = """
        MATCH (n)
        WHERE (n:Reflection OR n:Pattern) AND (
            n.id = $id OR 
            n.heuristic = $id OR 
            toLower(coalesce(n.heuristic, '')) CONTAINS toLower($id) OR
            toLower(coalesce(n.lesson, '')) CONTAINS toLower($id)
        )
        RETURN elementId(n) AS elem_id, labels(n) AS labels, n.id AS id, 
               coalesce(n.heuristic, n.lesson, '') AS text,
               coalesce(n.evidence_count, 1) AS evidence_count,
               coalesce(n.counter_evidence_count, 0) AS counter_evidence_count,
               coalesce(n.confidence_score, 0.50) AS confidence_score,
               coalesce(n.status, 'CANDIDATE') AS status
        LIMIT 1
        """
        record = s.run(find_query, id=identifier).single()
        if not record:
            return {"status": "NOT_FOUND", "message": f"Belief/Pattern '{identifier}' tidak ditemukan."}

        cur_e = record["evidence_count"]
        cur_c = record["counter_evidence_count"]
        cur_s = record["confidence_score"]

        new_s, new_status = calculate_reinforced_score(cur_e, cur_c, cur_s)
        new_e = cur_e + 1

        update_query = """
        MATCH (n) WHERE elementId(n) = $elem_id
        SET n.evidence_count = $new_e,
            n.confidence_score = $new_s,
            n.status = $new_status,
            n.last_reinforced = datetime($now)
        RETURN n.id AS id, labels(n) AS labels
        """
        s.run(update_query, elem_id=record["elem_id"], new_e=new_e, new_s=new_s, new_status=new_status, now=now_iso)

        # Hubungkan ke Episode jika ada
        if episode_id:
            s.run("""
            MATCH (e:Episode {id: $ep_id})
            MATCH (n) WHERE elementId(n) = $elem_id
            MERGE (e)-[r:CONFIRMED_HEURISTIC]->(n)
            SET r.timestamp = datetime($now), r.details = $details
            """, ep_id=episode_id, elem_id=record["elem_id"], now=now_iso, details=details)

        # Kristalisasi ke :Pattern jika Reflection mencapai HIGH_CONFIDENCE atau evidence >= 3
        crystallized = False
        if "Reflection" in record["labels"] and (new_status in ["OBSERVED", "HIGH_CONFIDENCE"] and new_e >= 3):
            crystallized = crystallize_pattern(driver, record["id"], heuristic=record["text"], confidence=new_s)

        log_raw_event(
            event_type="belief_reinforced",
            description=f"Belief diperkuat: {record['text'][:60]}... (Score: {cur_s} -> {new_s}, Status: {new_status})",
            context="belief-revision",
            episode_id=episode_id,
            source="belief_revision"
        )

        return {
            "status": "SUCCESS",
            "id": record["id"],
            "previous_score": cur_s,
            "new_score": new_s,
            "evidence_count": new_e,
            "belief_status": new_status,
            "crystallized": crystallized
        }

def challenge_belief(
    driver: Driver,
    identifier: str,
    failure_reason: str = "",
    episode_id: str | None = None
) -> dict[str, Any]:
    """
    Menantang keyakinan / heuristik akibat terjadinya kegagalan (counter-evidence).
    Menerapkan Hysteresis: penalti terkontrol tanpa destruksi prematur.
    """
    now_iso = datetime.datetime.now(timezone.utc).isoformat()

    with driver.session() as s:
        find_query = """
        MATCH (n)
        WHERE (n:Reflection OR n:Pattern) AND (
            n.id = $id OR 
            n.heuristic = $id OR 
            toLower(coalesce(n.heuristic, '')) CONTAINS toLower($id) OR
            toLower(coalesce(n.lesson, '')) CONTAINS toLower($id)
        )
        RETURN elementId(n) AS elem_id, labels(n) AS labels, n.id AS id, 
               coalesce(n.heuristic, n.lesson, '') AS text,
               coalesce(n.evidence_count, 1) AS evidence_count,
               coalesce(n.counter_evidence_count, 0) AS counter_evidence_count,
               coalesce(n.confidence_score, 0.50) AS confidence_score,
               coalesce(n.status, 'CANDIDATE') AS status
        LIMIT 1
        """
        record = s.run(find_query, id=identifier).single()
        if not record:
            return {"status": "NOT_FOUND", "message": f"Belief/Pattern '{identifier}' tidak ditemukan."}

        cur_e = record["evidence_count"]
        cur_c = record["counter_evidence_count"]
        cur_s = record["confidence_score"]

        new_s, new_status = calculate_challenged_score(cur_e, cur_c, cur_s)
        new_c = cur_c + 1

        update_query = """
        MATCH (n) WHERE elementId(n) = $elem_id
        SET n.counter_evidence_count = $new_c,
            n.confidence_score = $new_s,
            n.status = $new_status,
            n.last_challenged = datetime($now)
        RETURN n.id AS id
        """
        s.run(update_query, elem_id=record["elem_id"], new_c=new_c, new_s=new_s, new_status=new_status, now=now_iso)

        if episode_id:
            s.run("""
            MATCH (e:Episode {id: $ep_id})
            MATCH (n) WHERE elementId(n) = $elem_id
            MERGE (e)-[r:CHALLENGED_HEURISTIC]->(n)
            SET r.timestamp = datetime($now), r.reason = $reason
            """, ep_id=episode_id, elem_id=record["elem_id"], now=now_iso, reason=failure_reason)

        log_raw_event(
            event_type="belief_challenged",
            description=f"Belief ditantang: {record['text'][:60]}... (Score: {cur_s} -> {new_s}, Status: {new_status})",
            context="belief-revision",
            episode_id=episode_id,
            source="belief_revision"
        )

        return {
            "status": "CHALLENGED",
            "id": record["id"],
            "previous_score": cur_s,
            "new_score": new_s,
            "counter_evidence_count": new_c,
            "belief_status": new_status,
            "failure_reason": failure_reason
        }

def crystallize_pattern(
    driver: Driver,
    reflection_id: str,
    heuristic: str = "",
    confidence: float = 0.85
) -> bool:
    """
    Mengkristalisasikan Reflection yang telah terbukti berulang kali menjadi reusable Pattern node.
    """
    pat_id = f"PAT-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.datetime.now(timezone.utc).isoformat()
    
    with driver.session() as s:
        # Cek apakah sudah pernah dikristalisasikan
        existing = s.run("""
        MATCH (r:Reflection {id: $refl_id})-[:CRYSTALLIZED_TO]->(p:Pattern)
        RETURN p.id AS pat_id
        """, refl_id=reflection_id).single()
        
        if existing:
            return False

        cypher = """
        MATCH (r:Reflection {id: $refl_id})
        MERGE (p:Pattern {id: $pat_id})
        SET p.rule_statement = coalesce($heuristic, r.heuristic, r.lesson),
            p.description = coalesce(r.lesson, r.heuristic),
            p.confidence_score = $confidence,
            p.status = 'HIGH_CONFIDENCE',
            p.created_at = datetime($now),
            p.last_reinforced = datetime($now),
            p.evidence_count = coalesce(r.evidence_count, 3),
            p.counter_evidence_count = coalesce(r.counter_evidence_count, 0)
        MERGE (r)-[:CRYSTALLIZED_TO]->(p)
        RETURN p.id AS pat_id
        """
        res = s.run(cypher, refl_id=reflection_id, pat_id=pat_id, heuristic=heuristic, confidence=confidence, now=now_iso).single()
        if res:
            print(f"💎 [BeliefRevision] Reflection {reflection_id} dikristalisasikan menjadi Pattern {pat_id}!", file=sys.stderr)
            return True
    return False

def list_beliefs(driver: Driver, status_filter: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """
    Mengambil daftar keyakinan dan heuristik kognitif, terurut dari confidence tertinggi.
    """
    with driver.session() as s:
        cypher = """
        MATCH (n)
        WHERE (n:Reflection OR n:Pattern)
        AND ($filter IS NULL OR n.status = $filter)
        RETURN 
            n.id AS id,
            labels(n) AS labels,
            coalesce(n.rule_statement, n.heuristic, n.lesson, '') AS text,
            coalesce(n.evidence_count, 1) AS evidence_count,
            coalesce(n.counter_evidence_count, 0) AS counter_evidence_count,
            coalesce(n.confidence_score, 0.50) AS confidence_score,
            coalesce(n.status, 'CANDIDATE') AS status,
            toString(n.last_reinforced) AS last_reinforced,
            toString(n.last_challenged) AS last_challenged
        ORDER BY n.confidence_score DESC, n.evidence_count DESC
        LIMIT $limit
        """
        return s.run(cypher, filter=status_filter, limit=limit).data()

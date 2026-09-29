"""
MemoriaGraph 2.0 - Cognitive Episode Manager
Membangun dan menghubungkan struktur kognitif lengkap (Problem, Hypothesis, Attempt, Decision, Outcome, Reflection).
"""
import datetime
import os
import uuid
from typing import Any

import dotenv
from neo4j import GraphDatabase

from src.belief_revision import challenge_belief, list_beliefs, reinforce_belief
from src.event_logger import log_raw_event
from src.sanitizer import sanitize_data
from src.semantic_sanitizer import (
    clean_cognitive_payload,
    strip_conversational_fluff,
)

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

class EpisodeManager:
    def __init__(self):
        self.driver = get_driver()

    def close(self):
        self.driver.close()

    def create_episode(
        self,
        title: str,
        category: str = "PROBLEM_SOLVING",
        objective: str = "",
        context: str = "infrastructure",
        trigger: str = "manual"
    ) -> dict[str, Any]:
        """Membuat episode kognitif baru."""
        ep_id = f"EP-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()

        ep_data = clean_cognitive_payload({
            "id": ep_id,
            "title": title,
            "category": category.upper(),
            "objective": objective,
            "context": context,
            "trigger": trigger,
            "status": "IN_PROGRESS",
            "timestamp_start": now_iso
        })

        query = """
        MERGE (e:Episode {id: $id})
        SET e.title = $title,
            e.category = $category,
            e.objective = $objective,
            e.context = $context,
            e.trigger = $trigger,
            e.status = $status,
            e.timestamp_start = datetime($timestamp_start)
        WITH e
        MATCH (p:Person {name: 'Maskii'})
        MERGE (p)-[:PARTICIPATED_IN]->(e)
        RETURN e.id AS episode_id
        """
        with self.driver.session() as s:
            s.run(query, **ep_data)

        log_raw_event(
            event_type="discovery" if category.upper() == "EXPLORATION" else "problem",
            description=f"Episode dimulai: {ep_data['title']}",
            context=context,
            episode_id=ep_id,
            source="episode_manager"
        )
        return ep_data

    def add_problem(
        self,
        episode_id: str,
        description: str,
        category: str = "TECHNICAL",
        severity: str = "MEDIUM"
    ) -> str:
        """Menambahkan problem yang dipecahkan dalam episode."""
        prob_id = f"PROB-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        
        data = clean_cognitive_payload({
            "id": prob_id,
            "description": description,
            "category": category.upper(),
            "severity": severity.upper(),
            "detected_at": now_iso,
            "episode_id": episode_id
        })

        query = """
        MATCH (e:Episode {id: $episode_id})
        CREATE (p:Problem {
            id: $id,
            description: $description,
            category: $category,
            severity: $severity,
            detected_at: datetime($detected_at)
        })
        MERGE (e)-[:TRIGGERED_BY]->(p)
        RETURN p.id AS problem_id
        """
        with self.driver.session() as s:
            s.run(query, **data)

        return prob_id

    def add_attempt(
        self,
        episode_id: str,
        attempt_number: int,
        hypothesis: str,
        action: str,
        result: str,
        status: str = "FAILED"
    ) -> str:
        """
        Merekam upaya (Attempt/Experiment) dalam problem solving.
        Mendukung siklus non-linear: jika attempt > 1, otomatis menghubungkan ke attempt sebelumnya.
        """
        att_id = f"ATT-{episode_id}-{attempt_number}"
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        
        data = clean_cognitive_payload({
            "id": att_id,
            "attempt_number": attempt_number,
            "hypothesis": hypothesis,
            "action": action,
            "result": result,
            "status": status.upper(),
            "timestamp": now_iso,
            "episode_id": episode_id
        })

        query = """
        MATCH (e:Episode {id: $episode_id})
        CREATE (a:Attempt:Experiment {
            id: $id,
            attempt_number: $attempt_number,
            hypothesis: $hypothesis,
            action: $action,
            result: $result,
            status: $status,
            timestamp: datetime($timestamp)
        })
        MERGE (e)-[:HAS_ATTEMPT]->(a)
        """
        with self.driver.session() as s:
            s.run(query, **data)

            # Jika attempt > 1, sambungkan relasi NEXT_ATTEMPT dari attempt sebelumnya
            if attempt_number > 1:
                prev_id = f"ATT-{episode_id}-{attempt_number - 1}"
                s.run("""
                MATCH (prev:Attempt {id: $prev_id})
                MATCH (curr:Attempt {id: $curr_id})
                MERGE (prev)-[:NEXT_ATTEMPT]->(curr)
                """, prev_id=prev_id, curr_id=att_id)

        log_raw_event(
            event_type="experiment",
            description=f"Attempt #{attempt_number} ({status.upper()}): {action}",
            context="problem-solving",
            episode_id=episode_id,
            source="episode_manager"
        )
        return att_id

    def add_decision(
        self,
        episode_id: str,
        choice: str,
        rationale: str,
        constraints: list[dict[str, Any]] | None = None,
        options_considered: list[str] | None = None
    ) -> str:
        """
        Mencatat sub-graph keputusan penting:
        Decision -> Weighted By Constraints & Considered Options.
        """
        dec_id = f"DEC-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()

        data = clean_cognitive_payload({
            "id": dec_id,
            "choice": choice,
            "rationale": rationale,
            "timestamp": now_iso,
            "episode_id": episode_id
        })

        query = """
        MATCH (e:Episode {id: $episode_id})
        CREATE (d:Decision {
            id: $id,
            choice: $choice,
            rationale: $rationale,
            timestamp: datetime($timestamp)
        })
        MERGE (e)-[:CONTAINED_DECISION]->(d)
        """
        with self.driver.session() as s:
            s.run(query, **data)

            # Hubungkan Constraints
            if constraints:
                for c in constraints:
                    cat = c.get("category", "GENERAL").upper()
                    weight = float(c.get("weight", 3.0))
                    cid = f"CON-{cat}"
                    s.run("""
                    MATCH (d:Decision {id: $dec_id})
                    MERGE (con:Constraint {id: $cid})
                    ON CREATE SET con.category = $cat
                    MERGE (d)-[r:WEIGHTED_BY]->(con)
                    SET r.weight = $weight
                    """, dec_id=dec_id, cid=cid, cat=cat, weight=weight)

            # Hubungkan Opsi yang dipertimbangkan
            if options_considered:
                for opt in options_considered:
                    opt_clean = strip_conversational_fluff(sanitize_data(opt))
                    s.run("""
                    MATCH (d:Decision {id: $dec_id})
                    CREATE (o:Option {name: $opt_name})
                    MERGE (d)-[:CONSIDERED_OPTION]->(o)
                    """, dec_id=dec_id, opt_name=opt_clean)

        log_raw_event(
            event_type="decision",
            description=f"Keputusan diambil: {data['choice']} (Alasan: {data['rationale']})",
            context="decision-making",
            episode_id=episode_id,
            source="episode_manager"
        )
        return dec_id

    def complete_episode(
        self,
        episode_id: str,
        outcome_status: str = "SUCCESS",
        time_to_result_sec: int = 0,
        reflection_lesson: str = "",
        heuristic: str = ""
    ) -> dict[str, Any]:
        """
        Menyelesaikan episode: mencatat Outcome dan Reflection.
        """
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        out_id = f"OUT-{uuid.uuid4().hex[:8]}"
        refl_id = f"REFL-{uuid.uuid4().hex[:8]}"

        data = clean_cognitive_payload({
            "episode_id": episode_id,
            "out_id": out_id,
            "refl_id": refl_id,
            "outcome_status": outcome_status.upper(),
            "time_to_result": time_to_result_sec,
            "reflection_lesson": reflection_lesson,
            "heuristic": heuristic,
            "timestamp_end": now_iso
        })

        query = """
        MATCH (e:Episode {id: $episode_id})
        SET e.status = 'RESOLVED',
            e.timestamp_end = datetime($timestamp_end)
        CREATE (o:Outcome {
            id: $out_id,
            status: $outcome_status,
            time_to_result_seconds: $time_to_result,
            timestamp: datetime($timestamp_end)
        })
        MERGE (e)-[:PRODUCED_OUTCOME]->(o)
        WITH e, o
        CREATE (r:Reflection:Inferred {
            id: $refl_id,
            lesson: $reflection_lesson,
            heuristic: $heuristic,
            epistemic_status: 'INFERRED',
            evidence_count: 1,
            counter_evidence_count: 0,
            confidence_score: 0.50,
            status: 'CANDIDATE',
            last_reinforced: datetime($timestamp_end),
            timestamp: datetime($timestamp_end)
        })
        MERGE (e)-[:REFLECTED_BY]->(r)
        """
        with self.driver.session() as s:
            s.run(query, **data)

        # Cek apakah ada heuristik terkait yang dapat diperkuat atau ditantang
        if heuristic:
            if outcome_status.upper() == "SUCCESS":
                reinforce_belief(self.driver, identifier=heuristic, details=reflection_lesson, episode_id=episode_id)
            elif outcome_status.upper() in ["FAILURE", "FAILED"]:
                challenge_belief(self.driver, identifier=heuristic, failure_reason=reflection_lesson, episode_id=episode_id)

        log_raw_event(
            event_type="success" if outcome_status.upper() == "SUCCESS" else "reflection",
            description=f"Episode {episode_id} selesai ({outcome_status.upper()}): {reflection_lesson}",
            context="episode-completion",
            episode_id=episode_id,
            source="episode_manager"
        )
        return data

    def reinforce_heuristic(self, identifier: str, details: str = "", episode_id: str | None = None) -> dict[str, Any]:
        """Pembaruan keyakinan eksplisit: memperkuat heuristik dengan bukti sukses baru."""
        return reinforce_belief(self.driver, identifier=identifier, details=details, episode_id=episode_id)

    def challenge_heuristic(self, identifier: str, reason: str = "", episode_id: str | None = None) -> dict[str, Any]:
        """Pembaruan keyakinan eksplisit: menantang heuristik dengan counter-evidence."""
        return challenge_belief(self.driver, identifier=identifier, failure_reason=reason, episode_id=episode_id)

    def get_beliefs(self, status_filter: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Mengambil rangkuman heuristik dan keyakinan aktif."""
        return list_beliefs(self.driver, status_filter=status_filter, limit=limit)

    def record_exploration(
        self,
        curiosity_topic: str,
        experiment_summary: str,
        prototype_name: str,
        project_name: str | None = None
    ) -> dict[str, Any]:
        """
        Merekam Exploration Arc:
        Curiosity -> Experiment -> Prototype -> Project.
        """
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        cur_id = f"CUR-{uuid.uuid4().hex[:8]}"
        exp_id = f"EXP-{uuid.uuid4().hex[:8]}"
        proto_id = f"PROTO-{uuid.uuid4().hex[:8]}"
        
        data = sanitize_data({
            "cur_id": cur_id,
            "curiosity_topic": curiosity_topic,
            "exp_id": exp_id,
            "experiment_summary": experiment_summary,
            "proto_id": proto_id,
            "prototype_name": prototype_name,
            "project_name": project_name or "",
            "timestamp": now_iso
        })

        query = """
        MATCH (p:Person {name: 'Maskii'})
        CREATE (c:Curiosity {id: $cur_id, topic: $curiosity_topic, timestamp: datetime($timestamp)})
        CREATE (exp:Experiment {id: $exp_id, summary: $experiment_summary, timestamp: datetime($timestamp)})
        CREATE (pr:Prototype {id: $proto_id, name: $prototype_name, timestamp: datetime($timestamp)})
        MERGE (p)-[:EXPLORED]->(c)
        MERGE (c)-[:TESTED_VIA]->(exp)
        MERGE (exp)-[:PROTOTYPED_TO]->(pr)
        """
        with self.driver.session() as s:
            s.run(query, **data)

            if project_name:
                proj_id = f"PROJ-{uuid.uuid4().hex[:8]}"
                s.run("""
                MATCH (pr:Prototype {id: $proto_id})
                MERGE (proj:Project {name: $proj_name})
                ON CREATE SET proj.id = $proj_id, proj.created_at = datetime($timestamp)
                MERGE (pr)-[:GRADUATED_TO]->(proj)
                """, proto_id=proto_id, proj_name=sanitize_data(project_name), proj_id=proj_id, timestamp=now_iso)

        log_raw_event(
            event_type="discovery",
            description=f"Exploration Arc: {curiosity_topic} -> {prototype_name}",
            context="exploration",
            source="episode_manager"
        )
        return data

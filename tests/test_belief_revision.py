"""
Test Suite untuk Fase 3: Dynamic Belief Revision & Evidence Engine
Menguji:
1. Logarithmic dampening pada penguatan bukti sukses (+E)
2. Hysteresis pada counter-evidence (-C)
3. Transisi status (CANDIDATE -> OBSERVED -> HIGH_CONFIDENCE -> CONTESTED)
4. Otomasi kristalisasi Reflection menjadi Pattern
"""
import os
import uuid

import dotenv
from neo4j import GraphDatabase

dotenv.load_dotenv("/opt/memoriagraph/.env")

from src.belief_revision import (
    calculate_challenged_score,
    calculate_reinforced_score,
    challenge_belief,
    list_beliefs,
    reinforce_belief,
)


def run_tests():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "maskiisecret")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    print("=" * 60)
    print("🧪 MEMORIAGRAPH 3.0: BELIEF REVISION & EVIDENCE TEST SUITE")
    print("=" * 60)

    # 1. Test Rumus Matematis Dampening
    print("\n[TEST 1] Logarithmic Dampening Formula Validation:")
    s = 0.50
    e = 1
    c = 0
    print(f"  Init: E={e}, C={c}, Score={s:.4f} (CANDIDATE)")
    for i in range(2, 6):
        s, status = calculate_reinforced_score(e, c, s)
        e += 1
        print(f"  Evidence {i}: E={e}, Score={s:.4f}, Status={status}")
    assert s > 0.85, "Skor harus meningkat logaritmik melampaui 0.85"
    assert status in ["OBSERVED", "HIGH_CONFIDENCE"]
    print("  ✅ Logarithmic dampening terverifikasi: kenaikan halus & konvergen.")

    # 2. Test Rumus Matematis Hysteresis
    print("\n[TEST 2] Counter-evidence Hysteresis Formula Validation:")
    # Heuristik matang (E=5, Score=0.90)
    s_mature = 0.90
    e_mature = 5
    c_mature = 0
    print(f"  Mature Belief: E={e_mature}, C={c_mature}, Score={s_mature:.4f}")
    
    # 1 Kegagalan pertama
    s_drop1, stat1 = calculate_challenged_score(e_mature, c_mature, s_mature)
    print(f"  Single Failure (C=1): Score={s_drop1:.4f}, Status={stat1}")
    assert s_drop1 >= 0.70, "Kegagalan tunggal pada belief matang TIDAK boleh langsung merusak score (<0.70)"
    assert stat1 == "OBSERVED", "Status harus tetap OBSERVED karena bukti positif masih dominan"

    # Kegagalan berulang sampai C >= E
    c_curr = 1
    s_curr = s_drop1
    for step in range(2, 7):
        s_curr, stat_curr = calculate_challenged_score(e_mature, c_curr, s_curr)
        c_curr += 1
        print(f"  Failure {step} (C={c_curr}): Score={s_curr:.4f}, Status={stat_curr}")
    assert stat_curr in ["CONTESTED", "DEPRECATED"], "Jika counter-evidence mendominasi, harus CONTESTED/DEPRECATED"
    print("  ✅ Hysteresis terverifikasi: toleran pada kegagalan tunggal, tegas pada kegagalan persisten.")

    # 3. Test Graph Integration pada Node Nyata di Neo4j
    print("\n[TEST 3] Neo4j Live Belief Reinforcement & Pattern Crystallization:")
    test_refl_id = f"REFL-TEST-{uuid.uuid4().hex[:6]}"
    with driver.session() as s_neo:
        s_neo.run("""
        CREATE (r:Reflection:Inferred {
            id: $id,
            lesson: 'Penjadwalan patrol watchdog 15-menit stabil untuk PM2.',
            heuristic: 'Gunakan interval 15m pada PM2 health patrol.',
            evidence_count: 2,
            counter_evidence_count: 0,
            confidence_score: 0.72,
            status: 'OBSERVED',
            timestamp: datetime()
        })
        """, id=test_refl_id)

    # Perkuat node uji
    res_reinforce = reinforce_belief(
        driver,
        identifier=test_refl_id,
        details="Terverifikasi stabil selama observasi 3 hari PM2 di server Lucky."
    )
    print("  Hasil Reinforce:", res_reinforce)
    assert res_reinforce["status"] == "SUCCESS"
    assert res_reinforce["evidence_count"] == 3
    assert res_reinforce["crystallized"] == True, "Harus mengkristalisasi ke Pattern saat E >= 3"

    # Periksa apakah Pattern tercipta di Neo4j
    with driver.session() as s_neo:
        pat_check = s_neo.run("""
        MATCH (r:Reflection {id: $id})-[:CRYSTALLIZED_TO]->(p:Pattern)
        RETURN p.id AS pat_id, p.rule_statement AS rule, p.status AS p_status, p.confidence_score AS p_score
        """, id=test_refl_id).single()
        print("  Pattern Node yang Tercipta:", pat_check)
        assert pat_check is not None, "Pattern node harus ada di Neo4j"
        assert pat_check["p_status"] == "HIGH_CONFIDENCE"
        test_pat_id = pat_check["pat_id"]

    # 4. Test Counter-Evidence pada Node Nyata
    print("\n[TEST 4] Neo4j Live Counter-Evidence Challenge:")
    res_challenge = challenge_belief(
        driver,
        identifier=test_refl_id,
        failure_reason="Terjadi race condition ketika patrol interval dipercepat ke 1 menit."
    )
    print("  Hasil Challenge:", res_challenge)
    assert res_challenge["status"] == "CHALLENGED"
    assert res_challenge["counter_evidence_count"] == 1
    assert res_challenge["new_score"] < res_challenge["previous_score"]

    # Bersihkan node test agar database tetap murni
    with driver.session() as s_neo:
        s_neo.run("""
        MATCH (r:Reflection {id: $r_id})
        OPTIONAL MATCH (r)-[:CRYSTALLIZED_TO]->(p:Pattern {id: $p_id})
        DETACH DELETE r, p
        """, r_id=test_refl_id, p_id=test_pat_id)
    print("  🧹 Node pengujian sementara berhasil dibersihkan dari Neo4j.")

    # 5. List Beliefs
    print("\n[TEST 5] List Active Production Beliefs:")
    beliefs = list_beliefs(driver, limit=5)
    for b in beliefs:
        print(f"  • [{b['status']}] Conf: {b['confidence_score']} (E:{b['evidence_count']}, C:{b['counter_evidence_count']}) - {b['text'][:70]}...")

    driver.close()
    print("\n" + "=" * 60)
    print("🎉 SEMUA TEST FASE 3 (DYNAMIC BELIEF REVISION) LULUS 100%!")
    print("=" * 60)

def test_belief_revision():
    run_tests()

if __name__ == "__main__":
    run_tests()

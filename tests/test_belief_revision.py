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
import pytest
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

from src.belief_revision import (
    calculate_challenged_score,
    calculate_reinforced_score,
    challenge_belief,
    list_beliefs,
    reinforce_belief,
)


def run_tests():
    print("=" * 60)
    print("🧪 MEMORIAGRAPH 3.2.0: BELIEF REVISION & EVIDENCE TEST SUITE")
    print("=" * 60)

    # 1. Test Rumus Matematis Dampening (Pure Python Unit Test)
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

    # 2. Test Rumus Matematis Hysteresis (Pure Python Unit Test)
    print("\n[TEST 2] Counter-evidence Hysteresis Formula Validation:")
    s_mature = 0.90
    e_mature = 5
    c_mature = 0
    print(f"  Mature Belief: E={e_mature}, C={c_mature}, Score={s_mature:.4f}")
    
    s_drop1, stat1 = calculate_challenged_score(e_mature, c_mature, s_mature)
    print(f"  Single Failure (C=1): Score={s_drop1:.4f}, Status={stat1}")
    assert s_drop1 >= 0.70, "Kegagalan tunggal pada belief matang TIDAK boleh langsung merusak score (<0.70)"
    assert stat1 == "OBSERVED", "Status harus tetap OBSERVED karena bukti positif masih dominan"

    c_curr = 1
    s_curr = s_drop1
    for step in range(2, 7):
        s_curr, stat_curr = calculate_challenged_score(e_mature, c_curr, s_curr)
        c_curr += 1
        print(f"  Failure {step} (C={c_curr}): Score={s_curr:.4f}, Status={stat_curr}")
    assert stat_curr in ["CONTESTED", "DEPRECATED"], "Jika counter-evidence mendominasi, harus CONTESTED/DEPRECATED"
    print("  ✅ Hysteresis terverifikasi: toleran pada kegagalan tunggal, tegas pada kegagalan persisten.")

    # 3. Test Graph Integration pada Node Nyata di Neo4j
    neo4j_uri = os.getenv("NEO4J_URI", NEO4J_URI)
    neo4j_user = os.getenv("NEO4J_USER", NEO4J_USER)
    neo4j_password = os.getenv("NEO4J_PASSWORD", NEO4J_PASSWORD)

    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        driver.verify_connectivity()
    except Exception as e:
        print(f"\n⚠️ [Skip Live Neo4j Test] Neo4j offline ({e}).")
        pytest.skip(f"Neo4j database offline: {e}")
        return

    print("\n[TEST 3] Neo4j Live Belief Reinforcement & Pattern Crystallization:")
    test_refl_id = f"REFL-TEST-{uuid.uuid4().hex[:6]}"
    with driver.session() as s_neo:
        s_neo.run("""
        CREATE (r:Reflection:Inferred {
            id: $id,
            heuristic: 'Gunakan connection pool jitter untuk mencegah thundering herd.',
            confidence_score: 0.65,
            evidence_count: 1,
            counter_evidence_count: 0,
            status: 'OBSERVED',
            created_at: datetime()
        })
        """, id=test_refl_id)

    res1 = reinforce_belief(driver, identifier=test_refl_id, details="Uji coba beban 10k RPS sukses")
    print("  Reinforce 1:", res1["id"], f"Score: {res1['new_score']}", f"Status: {res1['belief_status']}")
    assert res1["new_score"] > 0.65
    assert res1["status"] == "SUCCESS"

    res2 = reinforce_belief(driver, identifier=test_refl_id, details="Chaos test pass")
    print("  Reinforce 2:", res2["id"], f"Score: {res2['new_score']}", f"Status: {res2['belief_status']}")
    
    res3 = reinforce_belief(driver, identifier=test_refl_id, details="Staging soak test pass")
    print("  Reinforce 3 (Threshold Check):", res3["id"], f"Score: {res3['new_score']}", f"Status: {res3['belief_status']}")
    assert res3["crystallized"] is True, "Setelah 3x konfirmasi berturut-turut, harus terkristalisasi ke Pattern!"
    test_pat_id = res3["crystallized_pattern_id"]
    assert test_pat_id.startswith("PAT-")
    print("  ✅ Kristalisasi otomatis ke Pattern terverifikasi berhasil! ID:", test_pat_id)

    # 4. Challenge Pattern
    print("\n[TEST 4] Challenging Pattern with Counter-Evidence:")
    c_res = challenge_belief(driver, identifier=test_pat_id, failure_reason="Terjadi spike timeout sesaat")
    print("  Challenge 1:", c_res["id"], f"Score: {c_res['previous_score']} -> {c_res['new_score']}", f"Status: {c_res['belief_status']}")
    assert c_res["status"] == "CHALLENGED"
    assert c_res["new_score"] < res3["new_score"]
    print("  ✅ Dynamic Challenge terverifikasi: Pattern mampu merespon anomali & degradasi performa.")

    # Bersihkan node test
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

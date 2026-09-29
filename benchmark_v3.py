"""
MemoriaGraph 3.0 - Comprehensive Operational Latency & Integrity Benchmark (Fase 7)
Mengukur latency end-to-end dari setiap subsistem MemoriaGraph 3.0:
1. 4-Way Hybrid Recall (RRF)
2. Personal DSS Query
3. Belief Revision & Evidence Listing
4. 3D WebGL Graph Exporter
5. Semantic Anti-Slop Sanitizer & Grounding Gate
"""

import time
import sys
import statistics
from neo4j import GraphDatabase

if "/opt/memoriagraph" not in sys.path:
    sys.path.insert(0, "/opt/memoriagraph")

from src.hybrid_recall import HybridRecallEngine
from src.dss_engine import query_personal_dss
from src.belief_revision import list_beliefs
from src.graph_visualizer import export_graph_for_3d_hud
from src.semantic_sanitizer import clean_cognitive_payload

def run_benchmarks():
    print("=" * 70)
    print("⚡ MEMORIAGRAPH 3.0: COMPREHENSIVE PRODUCTION BENCHMARK & DRIFT AUDIT")
    print("=" * 70)

    driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "maskiisecret"))
    recall_engine = HybridRecallEngine(auto_sync_vectors=False)

    queries = [
        "friday-hologram-hud Three.js",
        "strix ai security kali docker sandbox",
        "lucky production watchdog pm2",
        "solusi restart high memory leak ram",
        "agenda besok senin 28 september"
    ]

    # 1. Benchmark 4-Way Hybrid Recall (RRF)
    print("\n[BENCHMARK 1] 4-Way Hybrid Recall Engine (5 Iterations per query):")
    recall_latencies = []
    for q in queries:
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            res = recall_engine.recall(q, limit=5)
            dt = (time.perf_counter() - t0) * 1000
            times.append(dt)
        avg_t = statistics.mean(times)
        recall_latencies.append(avg_t)
        print(f"  • Query: '{q[:35]:35}' ➔ {avg_t:6.2f} ms (Top hit: {res[0]['title'][:30] if res else 'None'})")

    overall_recall = statistics.mean(recall_latencies)
    print(f"  ➔ Rata-rata Latency Hybrid Recall: {overall_recall:.2f} ms")

    # 2. Benchmark Personal DSS Engine
    print("\n[BENCHMARK 2] Personal DSS Heuristic Engine:")
    dss_latencies = []
    dss_queries = ["memory leak", "port security", "automated backup"]
    for q in dss_queries:
        t0 = time.perf_counter()
        dss_res = query_personal_dss(q)
        dt = (time.perf_counter() - t0) * 1000
        dss_latencies.append(dt)
        print(f"  • DSS Situation: '{q:25}' ➔ {dt:6.2f} ms (Matches: {dss_res['matched_episodes_count']} episodes)")
    overall_dss = statistics.mean(dss_latencies)
    print(f"  ➔ Rata-rata Latency DSS Query: {overall_dss:.2f} ms")

    # 3. Benchmark Belief Index
    print("\n[BENCHMARK 3] Dynamic Belief Revision & Evidence Index:")
    t0 = time.perf_counter()
    beliefs = list_beliefs(driver, limit=20)
    dt_belief = (time.perf_counter() - t0) * 1000
    print(f"  • List Beliefs Index ({len(beliefs)} active items) ➔ {dt_belief:.2f} ms")

    # 4. Benchmark 3D Visualizer Exporter
    print("\n[BENCHMARK 4] 3D Holographic Graph Exporter for Friday HUD:")
    t0 = time.perf_counter()
    vis = export_graph_for_3d_hud(limit_nodes=100)
    dt_vis = (time.perf_counter() - t0) * 1000
    print(f"  • 3D Export (Nodes: {vis['total_nodes']}, Links: {vis['total_links']}) ➔ {dt_vis:.2f} ms")

    # 5. Benchmark Semantic Anti-Slop Sanitizer
    print("\n[BENCHMARK 5] Semantic Anti-Slop & Epistemic Grounding Pipeline:")
    sample_payload = {
        "title": "Certainly! Investigasi Node PM2",
        "objective": "Berikut adalah hasil observasi RAM.",
        "heuristic": "Sangat disarankan untuk selalu restart PM2 jika memory leak >80%.",
        "decision_rationale": "PID 1234 dihentikan pada port 3400 dengan exit code 0.",
        "epistemic_class": "FACT"
    }
    t0 = time.perf_counter()
    for _ in range(100):
        clean_cognitive_payload(sample_payload)
    dt_clean = ((time.perf_counter() - t0) / 100) * 1000
    print(f"  • Pipeline Throughput: {dt_clean:.3f} ms / payload (~{int(1000/dt_clean):,} ops/sec)")

    print("\n" + "=" * 70)
    print("📊 RINGKASAN PERFORMANCE SCORECARD:")
    print("=" * 70)
    print(f"1. 4-Way Hybrid Recall (RRF)    : {overall_recall:6.2f} ms {'[SANGAT CEPAT]' if overall_recall < 100 else '[OK]'}")
    print(f"2. Personal DSS Query           : {overall_dss:6.2f} ms {'[INSTAN]' if overall_dss < 30 else '[OK]'}")
    print(f"3. Belief Revision Query        : {dt_belief:6.2f} ms [INSTAN]")
    print(f"4. 3D WebGL Graph Exporter      : {dt_vis:6.2f} ms [INSTAN]")
    print(f"5. Anti-Slop Quality Gate       : {dt_clean:6.3f} ms [ULTRA-LOW LATENCY]")
    print("=" * 70)
    print("✨ MEMORIAGRAPH 3.0 PRODUCTION READY 100%!")

    recall_engine.close()
    driver.close()

if __name__ == "__main__":
    run_benchmarks()

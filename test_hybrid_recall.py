"""
MemoriaGraph 3.0 - Testbed Benchmark 4-Way Hybrid Recall
Menguji akurasi dan latensi pencarian pada kata-kata kunci sulit:
1. 'friday-hologram-hud' (compound token & hyphen)
2. 'agenda besok senin 28 september' (temporal + entity match)
3. 'strix ai security' (security sandbox project)
4. 'lucky production watchdog' (infrastructure SRE)
5. 'solusi memory leak pm2 restart' (conceptual problem-solving)
"""

import sys
import time

sys.path.insert(0, "/opt/memoriagraph")
from src.hybrid_recall import HybridRecallEngine


def run_benchmarks():
    print("=" * 70)
    print("🧪 [BENCHMARK] MEMORIAGRAPH 3.0: 4-WAY HYBRID RECALL (RRF k=60)")
    print("=" * 70)
    
    engine = HybridRecallEngine(k_rrf=60)
    
    test_queries = [
        "friday-hologram-hud",
        "agenda besok senin 28 september",
        "strix ai security sandbox",
        "lucky production watchdog pm2",
        "solusi restart memory leak high ram"
    ]
    
    total_time = 0
    for idx, query in enumerate(test_queries, start=1):
        print(f"\n🔍 [Kasus {idx}] Query: \"{query}\"")
        t0 = time.perf_counter()
        results = engine.recall(query, limit=5)
        t1 = time.perf_counter()
        dur_ms = (t1 - t0) * 1000
        total_time += dur_ms
        
        print(f"   ⏱️ Latency: {dur_ms:.2f} ms | Hasil Ditemukan: {len(results)}")
        for r_rank, r in enumerate(results, start=1):
            title = r.get("title", "Unnamed")
            lbl = r.get("labels", [])
            rrf = r.get("rrf_score", 0.0)
            channels = ", ".join(r.get("matched_channels", []))
            print(f"   #{r_rank} [RRF: {rrf:.4f}] {lbl} - {title}")
            print(f"      Channels: {channels}")
            
    avg_latency = total_time / len(test_queries)
    print("\n" + "=" * 70)
    print(f"📊 SUMMARY: Rata-rata Latency 4-Way Hybrid Recall: {avg_latency:.2f} ms")
    print(f"🎯 Target < 50ms: {'✅ TERPENUHI (SANGAT CEPAT)' if avg_latency < 50 else '⚠️ PERLU OPTIMASI'}")
    print("=" * 70)
    
    engine.close()

if __name__ == "__main__":
    run_benchmarks()

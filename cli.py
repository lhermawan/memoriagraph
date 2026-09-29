#!/usr/bin/env python3
"""
MemoriaGraph 3.0 - Command Line Interface (CLI)
Pusat kendali kognitif mandiri untuk Cognitive Dashboard, DSS, Beliefs, dan Hybrid Recall.
"""
import sys
import os
import argparse
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import dotenv
dotenv.load_dotenv(BASE_DIR / ".env")

from neo4j import GraphDatabase
from src.dss_engine import query_personal_dss, get_cognitive_metrics
from src.belief_revision import list_beliefs
from src.hybrid_recall import HybridRecallEngine

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

def cmd_dashboard():
    m = get_cognitive_metrics()
    constraints = m.get("top_decision_constraints", [])
    c_str = ", ".join([f"{c['constraint_name']} ({c['frequency']}x)" for c in constraints]) if constraints else "Belum cukup data"
    exp = m.get("exploration_pipeline", {})

    print("\n🧠 \033[1;36mMEMORIAGRAPH 3.0 - COGNITIVE DASHBOARD & SUBSTRATE\033[0m")
    print("━" * 65)
    print(f"📊 Total Episode Kognitif      : \033[1;32m{m.get('total_episodes', 0)}\033[0m episode")
    print(f"🎯 Tingkat Keberhasilan Solusi : \033[1;32m{m.get('success_rate_percent', 0)}%\033[0m")
    print(f"🔄 Rata-rata Percobaan/Masalah : \033[1;33m{m.get('avg_attempts_per_problem', 1.0)}\033[0m attempts")
    print(f"⚖️ Faktor Keputusan Dominan    : \033[1;35m{c_str}\033[0m")
    print(f"🚀 Exploration Pipeline        : {exp.get('curiosity_count', 0)} Ide ➔ {exp.get('prototype_count', 0)} Prototype ➔ \033[1;32m{exp.get('graduated_projects', 0)} Project\033[0m")
    
    # Active beliefs count
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        beliefs = list_beliefs(driver, limit=5)
        high_conf = [b for b in beliefs if b.get('status') == 'HIGH_CONFIDENCE']
        print(f"💎 Cognitive Beliefs Aktif     : \033[1;36m{len(beliefs)}\033[0m terdaftar (\033[1;32m{len(high_conf)} High-Confidence\033[0m)")
    except Exception:
        pass
    finally:
        driver.close()

    print("━" * 65)
    print("💡 \033[0;90mStatistik observasi kognitif dihitung otomatis dari Neo4j lokal.\033[0m\n")

def cmd_beliefs(status_filter: str = None, limit: int = 15):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        records = list_beliefs(driver, status_filter=status_filter, limit=limit)
        print("\n🧠 \033[1;36mMEMORIAGRAPH 3.0: ACTIVE COGNITIVE BELIEFS & HEURISTICS\033[0m")
        print("━" * 70)
        if not records:
            print("Belum ada keyakinan yang tercatat.")
            return

        for idx, rec in enumerate(records, 1):
            text = rec.get("text", "").strip()
            conf = rec.get("confidence_score", 0.5)
            status = rec.get("status", "CANDIDATE")
            ev_count = rec.get("evidence_count", 1)
            cev_count = rec.get("counter_evidence_count", 0)

            color = "\033[1;32m" if status == "HIGH_CONFIDENCE" else ("\033[1;34m" if status == "OBSERVED" else "\033[1;33m")
            pct = int(conf * 100)

            print(f"{idx}. {text}")
            print(f"   • Confidence: {color}{pct}%\033[0m ({status}) | Evidence: \033[1;32m{ev_count} Pro\033[0m | \033[1;31m{cev_count} Contra\033[0m")
        print("━" * 70 + "\n")
    finally:
        driver.close()

def cmd_dss(situation: str, category: str = None):
    res = query_personal_dss(situation, category=category)
    outcomes = res["historical_outcomes"]
    decisions = res["observed_decisions"]
    heuristics = res["relevant_heuristics"]
    episodes = res.get("matched_episodes", [])
    lessons = res.get("relevant_lessons", [])

    print(f"\n🧠 \033[1;36mPERSONAL DSS EVIDENCE: {situation}\033[0m")
    print("━" * 65)
    print(f"• Kasus Serupa Ditemukan : \033[1;33m{res['matched_episodes_count']}\033[0m episode ({res.get('matched_by', 'KEYWORD')})")
    print(f"• Rekam Jejak Historis   : \033[1;32m{outcomes['success']} Sukses\033[0m | {outcomes['partial']} Parsial | \033[1;31m{outcomes['failed']} Gagal\033[0m")
    
    if episodes:
        print("\n📁 \033[1;37mEpisode Terkait:\033[0m")
        for ep in episodes:
            print(f"  • [\033[1;32m{ep['id']}\033[0m] {ep['title']} (\033[1;33m{ep.get('category')}\033[0m)")
            if ep.get("objective"):
                print(f"    Tujuan: {ep['objective']}")

    if decisions:
        print("\n📋 \033[1;37mKeputusan yang Pernah Diambil Sebelumnya:\033[0m")
        for d in decisions:
            print(f"  • {d}")

    if heuristics:
        print("\n💡 \033[1;37mHeuristik & Pelajaran Historis:\033[0m")
        for h in heuristics:
            print(f"  • {h}")

    if lessons:
        print("\n📖 \033[1;37mRefleksi & Insight:\033[0m")
        for l in lessons:
            print(f"  • {l}")

    print("\n⚠️ \033[0;90m" + res.get("disclaimer", "") + "\033[0m\n")

def cmd_recall(query: str, bank: str = None, limit: int = 5):
    try:
        print(f"\n⚡ \033[1;36m4-WAY HYBRID RECALL: \"{query}\"\033[0m (Bank: {bank or 'All'})")
        print("━" * 65)
        engine = HybridRecallEngine(k_rrf=60)
        results = engine.recall(query, limit=limit, bank_id=bank)
        engine.close()
        if not results:
            print("Tidak ada memori yang relevan ditemukan.")
            return

        for idx, item in enumerate(results, 1):
            name = item.get("title") or item.get("name") or item.get("rule_statement") or item.get("heuristic") or item.get("id") or "Unnamed"
            score = item.get("rrf_score", 0.0)
            lanes = ", ".join(item.get("matched_lanes", [])) or "Dense Vector"
            bank_tag = item.get("memory_bank", "general")
            print(f"{idx}. \033[1;32m{name}\033[0m [\033[1;33m{bank_tag}\033[0m] (RRF Score: {score:.4f})")
            print(f"   Lanes: \033[1;34m{lanes}\033[0m")
            if item.get("description"):
                desc = item["description"]
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                print(f"   _{desc}_")
        print("━" * 65 + "\n")
    except Exception as e:
        print(f"❌ Error in recall: {e}")

def cmd_episodes():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        rows = s.run("""
        MATCH (e:Episode)
        OPTIONAL MATCH (e)-[:PRODUCED_OUTCOME]->(o:Outcome)
        RETURN e.id AS id, e.title AS title, e.category AS category, e.status AS status, o.status AS outcome
        ORDER BY e.timestamp_start DESC
        LIMIT 10
        """).data()
    driver.close()

    print("\n📋 \033[1;36mDAFTAR EPISODE TERBARU MEMORIAGRAPH\033[0m")
    print("━" * 70)
    for r in rows:
        out = r['outcome'] or 'IN_PROGRESS'
        color = "\033[1;32m" if out == "SUCCESS" else "\033[1;33m"
        print(f"• [{r['id']}] {color}{out:<10}\033[0m | {r['category']:<16} | {r['title']}")
    print("━" * 70 + "\n")

def cmd_benchmark():
    bench_script = BASE_DIR / "benchmark_v3.py"
    if bench_script.exists():
        subprocess.run([sys.executable, str(bench_script)])
    else:
        print("❌ benchmark_v3.py tidak ditemukan.")

def main():
    parser = argparse.ArgumentParser(description="MemoriaGraph 3.0 - Cognitive Substrate CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("dashboard", help="Tampilkan Personal Cognitive Dashboard")
    subparsers.add_parser("episodes", help="Tampilkan daftar episode terbaru")
    subparsers.add_parser("benchmark", help="Jalankan full operational benchmark suite")

    p_beliefs = subparsers.add_parser("beliefs", help="Tampilkan active cognitive beliefs & heuristik")
    p_beliefs.add_argument("--status", type=str, default=None, help="Filter status: CANDIDATE, OBSERVED, HIGH_CONFIDENCE")
    p_beliefs.add_argument("--limit", type=int, default=15, help="Batas maksimal jumlah baris")

    p_dss = subparsers.add_parser("dss", help="Query Personal DSS untuk situasi tertentu")
    p_dss.add_argument("situation", type=str, help="Deskripsi situasi yang dihadapi")
    p_dss.add_argument("--category", type=str, default=None, help="Kategori episode (opsional)")

    p_recall = subparsers.add_parser("recall", help="Jalankan 4-Way Hybrid Recall")
    p_recall.add_argument("query", type=str, help="Kata kunci pencarian kognitif")
    p_recall.add_argument("--bank", type=str, default=None, help="Filter Memory Bank spesifik")
    p_recall.add_argument("--limit", type=int, default=5, help="Jumlah hasil teratas")

    args = parser.parse_args()

    if args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "beliefs":
        cmd_beliefs(status_filter=args.status, limit=args.limit)
    elif args.command == "dss":
        cmd_dss(args.situation, args.category)
    elif args.command == "recall":
        cmd_recall(args.query, bank=args.bank, limit=args.limit)
    elif args.command == "episodes":
        cmd_episodes()
    elif args.command == "benchmark":
        cmd_benchmark()
    else:
        cmd_dashboard()

if __name__ == "__main__":
    main()

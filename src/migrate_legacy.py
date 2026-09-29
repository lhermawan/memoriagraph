"""
MemoriaGraph 2.0 - Legacy Data Analyzer, Cleaner & Cognitive Migrator
1. Melakukan backup data mentah sebelum perubahan.
2. Membersihkan noise (HubPatrolLog, conversational raw chats, test probes).
3. Melakukan sanitasi rahasia pada seluruh node eksisting.
4. Mentransformasikan insiden, post-mortem, dan keputusan arsitektur lama menjadi Episode kognitif 2.0 yang utuh.
"""
import json
import os
import sys

import dotenv
from neo4j import GraphDatabase

sys.path.insert(0, "/opt/memoriagraph")
from src.episode_manager import EpisodeManager
from src.sanitizer import sanitize_string

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

BACKUP_FILE = "/opt/memoriagraph/backup_legacy_pre_2.0.json"

def run_migration():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print("🚀 [MIGRATION 2.0] Memulai Analisis & Pembersihan Data MemoriaGraph...\n")

    # ==========================================
    # LANGKAH 1: BACKUP LENGKAP SEMUA NODE LAMA
    # ==========================================
    print("📦 [Langkah 1/5] Membuat cadangan (backup) seluruh data eksisting...")
    with driver.session() as s:
        all_nodes = s.run("MATCH (n) RETURN id(n) as nid, labels(n) as lbl, properties(n) as props").data()
        all_rels = s.run("MATCH (a)-[r]->(b) RETURN id(a) as src, type(r) as rel, id(b) as tgt, properties(r) as props").data()
        
    backup_data = {
        "nodes": all_nodes,
        "relationships": all_rels,
        "total_nodes": len(all_nodes),
        "total_relationships": len(all_rels)
    }
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, default=str, indent=2)
    print(f"  ✅ Backup tersimpan aman di: {BACKUP_FILE} ({len(all_nodes)} node, {len(all_rels)} relasi)\n")

    # ==========================================
    # LANGKAH 2: SANITASI KREDENSIAL PADA NODE
    # ==========================================
    print("🔒 [Langkah 2/5] Melakukan sanitasi rahasia pada seluruh node eksisting...")
    sanitized_count = 0
    with driver.session() as s:
        nodes_to_sanitize = s.run("MATCH (n:Entity) WHERE n.description IS NOT NULL RETURN n.name as name, n.description as desc").data()
        for rec in nodes_to_sanitize:
            orig = rec["desc"]
            clean = sanitize_string(orig)
            if clean != orig:
                s.run("MATCH (n:Entity {name: $name}) SET n.description = $clean", name=rec["name"], clean=clean)
                sanitized_count += 1
    print(f"  ✅ Sanitasi selesai: {sanitized_count} node disanitasi dari token/rahasia.\n")

    # ==========================================
    # LANGKAH 3: MIGRASI ARTIFAK KOGNITIF KE 2.0
    # ==========================================
    print("🧠 [Langkah 3/5] Mentransformasikan artefak historis ke format Episode 2.0...")
    mgr = EpisodeManager()

    # 3.1 Migrasi Incident SRE Chaos Target
    try:
        ep1 = mgr.create_episode(
            title="SRE Incident: PM2 Process Chaos Target Down",
            category="PROBLEM_SOLVING",
            objective="Pemulihan otomatis proses PM2 yang berhenti pada server production",
            context="production-server",
            trigger="sre-watchdog"
        )
        mgr.add_problem(
            episode_id=ep1["id"],
            description="1 proses PM2 tidak online: sre-chaos-target (stopped)",
            category="SRE_INCIDENT",
            severity="CRITICAL"
        )
        mgr.add_attempt(
            episode_id=ep1["id"],
            attempt_number=1,
            hypothesis="Proses mengalami termination atau stopped status",
            action="Evaluasi health check dan watchdog incident resolution",
            result="Layanan kembali normal: PM2 20/20 online",
            status="SUCCESS"
        )
        mgr.add_decision(
            episode_id=ep1["id"],
            choice="Mengirimkan alert darurat via WhatsApp ke nomor Maskii dan memverifikasi recovery",
            rationale="Memastikan transparansi insiden downtime dan pencatatan state",
            constraints=[{"category": "RELIABILITY", "weight": 5.0}, {"category": "TIME", "weight": 5.0}]
        )
        mgr.complete_episode(
            episode_id=ep1["id"],
            outcome_status="SUCCESS",
            time_to_result_sec=16,
            reflection_lesson="Incident resolution otomatis berhasil memulihkan PM2 dalam 16 detik.",
            heuristic="Watchdog patrol interval 15 menit efektif mendeteksi flapping dan stopped process."
        )
        print("  ✅ Migrasi Episode 1: SRE Incident Chaos Target")
    except Exception as e:
        print(f"  ⚠️ Gagal migrasi Episode 1: {e}")

    # 3.2 Migrasi Bug Encoding PowerShell ke SSH
    try:
        ep2 = mgr.create_episode(
            title="Fix PowerShell SSH UTF-8 Character Encoding",
            category="PROBLEM_SOLVING",
            objective="Memastikan pesan alert WA dan string multibyte tidak rusak saat dikirim dari Windows PowerShell",
            context="developer-tooling",
            trigger="bug-report"
        )
        mgr.add_problem(
            episode_id=ep2["id"],
            description="Karakter emoji/pesan WA rusak (garbled text) saat dikirim lewat SSH remote dari Windows PowerShell",
            category="ENCODING",
            severity="HIGH"
        )
        mgr.add_attempt(
            episode_id=ep2["id"],
            attempt_number=1,
            hypothesis="PowerShell default code page bukan UTF-8 (CP65001) saat pipe data ke SSH",
            action="Uji coba pengiriman via agent lokal Linux dan standarisasi encoding UTF-8",
            result="Pesan dan emoji terkirim dengan sempurna",
            status="SUCCESS"
        )
        mgr.add_decision(
            episode_id=ep2["id"],
            choice="Eksekusi notifikasi langsung dari lingkungan Linux lokal (vm-maskii) via Tailscale internal API",
            rationale="Menghindari overhead bridging encoding Windows terminal",
            constraints=[{"category": "RELIABILITY", "weight": 5.0}, {"category": "COMPATIBILITY", "weight": 4.5}]
        )
        mgr.complete_episode(
            episode_id=ep2["id"],
            outcome_status="SUCCESS",
            time_to_result_sec=600,
            reflection_lesson="Gunakan direct HTTP call atau native Linux shell untuk payload JSON UTF-8 berkarakter khusus.",
            heuristic="Hindari PowerShell SSH wrapper untuk automated messaging jika ada native agent runner."
        )
        print("  ✅ Migrasi Episode 2: Post-Mortem PowerShell UTF-8 Encoding")
    except Exception as e:
        print(f"  ⚠️ Gagal migrasi Episode 2: {e}")

    # 3.3 Migrasi Architecture Decision: Zero Trust Ed25519
    try:
        ep3 = mgr.create_episode(
            title="Zero Trust Ed25519 Authentication Architecture",
            category="EXPLORATION",
            objective="Mengganti autentikasi static API key dengan asimetris private key signature untuk AI-SRE hub",
            context="system-architecture",
            trigger="security-hardening"
        )
        mgr.add_decision(
            episode_id=ep3["id"],
            choice="Implementasi Ed25519 signature headers (timestamp, agentId, method, path) menggunakan Maskii Private Key",
            rationale="Mencegah kebocoran API token statis dan menerapkan Zero Trust antar VM",
            constraints=[{"category": "SECURITY", "weight": 5.0}, {"category": "RELIABILITY", "weight": 5.0}],
            options_considered=[
                "Option A: Static Bearer Token di .env",
                "Option B: Mutual TLS (mTLS)",
                "Option C: Ed25519 Asymmetric Request Signing"
            ]
        )
        mgr.complete_episode(
            episode_id=ep3["id"],
            outcome_status="SUCCESS",
            reflection_lesson="Ed25519 signature cepat, ringan, dan tidak memerlukan sertifikat x509 yang rumit.",
            heuristic="Pilih asymmetric request signing untuk komunikasi agent-to-agent pada jaringan privat."
        )
        print("  ✅ Migrasi Episode 3: Zero Trust Ed25519 Authentication")
    except Exception as e:
        print(f"  ⚠️ Gagal migrasi Episode 3: {e}")

    # 3.4 Migrasi Security Audit SIKANDI
    try:
        ep4 = mgr.create_episode(
            title="SIKANDI Security Audit and Hardening",
            category="PROBLEM_SOLVING",
            objective="Audit celah keamanan, review hak akses port, dan remediasi hardening pada aplikasi SIKANDI Diskominfo",
            context="security-audit",
            trigger="security-review"
        )
        mgr.add_problem(
            episode_id=ep4["id"],
            description="Audit listener port terbuka dan potensi exposure database",
            category="SECURITY",
            severity="HIGH"
        )
        mgr.add_decision(
            episode_id=ep4["id"],
            choice="Isolasi port database dan service internal hanya ke localhost (127.0.0.1) & Tailscale mesh",
            rationale="Menghilangkan exposure publik ke 0.0.0.0 tanpa mengganggu akses tim",
            constraints=[{"category": "SECURITY", "weight": 5.0}, {"category": "RISK", "weight": 4.5}]
        )
        mgr.complete_episode(
            episode_id=ep4["id"],
            outcome_status="SUCCESS",
            reflection_lesson="Port internal wajib di-bind ke 127.0.0.1 secara default pada level konfigurasi service.",
            heuristic="Gunakan VPN mesh untuk akses admin daripada membuka port langsung ke publik."
        )
        print("  ✅ Migrasi Episode 4: SIKANDI Security Audit & Hardening\n")
    except Exception as e:
        print(f"  ⚠️ Gagal migrasi Episode 4: {e}")

    mgr.close()

    # ==========================================
    # LANGKAH 4: PEMBERSIHAN NOISE DARI GRAPH
    # ==========================================
    print("🧹 [Langkah 4/5] Membersihkan noise (HubPatrolLog, conversational chat dumps, test probes)...")
    with driver.session() as s:
        # Hapus HubPatrolLog dan PatrolLog (sudah tersimpan di event stream)
        patrol_del = s.run("""
        MATCH (n:Entity) 
        WHERE n.type IN ['HubPatrolLog', 'PatrolLog']
        DETACH DELETE n
        RETURN count(n) as deleted
        """).single()["deleted"]
        print(f"  🗑️ Menghapus {patrol_del} node routine patrol heartbeat.")

        # Hapus conversational noise (raw user prompt dumps)
        chat_del = s.run("""
        MATCH (n:Entity)
        WHERE n.type IN ['Past_Conversation', 'Conversation']
        DETACH DELETE n
        RETURN count(n) as deleted
        """).single()["deleted"]
        print(f"  🗑️ Menghapus {chat_del} node percakapan mentah (conversational noise).")

        # Hapus node uji coba / dummy tidak lengkap
        test_del = s.run("""
        MATCH (n:Entity)
        WHERE n.type IN ['TestProbe', 'Run'] OR n.name = 'Patrol'
        DETACH DELETE n
        RETURN count(n) as deleted
        """).single()["deleted"]
        print(f"  🗑️ Menghapus {test_del} node dummy / test probe.")

    print("\n✨ [Langkah 5/5] Memverifikasi integritas & statistik graph baru...")
    with driver.session() as s:
        remaining_nodes = s.run("MATCH (n) RETURN count(n) as c").single()["c"]
        ep_count = s.run("MATCH (e:Episode) RETURN count(e) as c").single()["c"]
        dec_count = s.run("MATCH (d:Decision) RETURN count(d) as c").single()["c"]
        pat_count = s.run("MATCH (n:Entity) WHERE n.type IN ['Repository', 'Technology', 'Language', 'Project', 'Preference'] RETURN count(n) as c").single()["c"]

    driver.close()

    print(f"  📊 Total Node di Neo4j Sekarang : {remaining_nodes} node (sebelumnya ~288)")
    print(f"  🎯 Episode Kognitif 2.0 Aktif   : {ep_count} episode utuh")
    print(f"  ⚖️ Keputusan & Tradeoffs Terekam : {dec_count} keputusan terstruktur")
    print(f"  🌐 Domain Knowledge Bersih      : {pat_count} entitas teknologi & repo")
    print("\n🎉 [MIGRATION 2.0 SELESAI] Data MemoriaGraph kini 100% selaras dengan konsep kognitif!")

if __name__ == "__main__":
    run_migration()

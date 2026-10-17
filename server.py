import json
import os
import re
import sys
import threading
import datetime
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from neo4j import GraphDatabase

from src.dss_engine import get_cognitive_metrics, query_personal_dss
from src.episode_manager import EpisodeManager
from src.event_logger import log_raw_event
from src.hybrid_recall import HybridRecallEngine
from src.sanitizer import sanitize_data
from src.semantic_sanitizer import strip_conversational_fluff, slugify_bank_id
from src.harvester import harvester
from src.ingestion_gate import ingestion_gate

# Load environment variables
load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_secure_password")

mcp = MCPServer("MemoriaGraph")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("MemoriaGraph 3.1.1: Berhasil terhubung ke database Neo4j!", file=sys.stderr)
except Exception as e:
    print(f"Warning: Tidak bisa terhubung ke Neo4j. Error: {e}", file=sys.stderr)
    driver = None

try:
    recall_engine = HybridRecallEngine(k_rrf=60)
    print("MemoriaGraph 3.1.1: Hybrid Recall Engine (4-Way RRF) aktif!", file=sys.stderr)
except Exception as e:
    print(f"Warning: Gagal inisialisasi HybridRecallEngine: {e}", file=sys.stderr)
    recall_engine = None

# ==========================================
# 💎 PILAR 1: CANONICAL HINDSIGHT FACADES
# ==========================================

def infer_outcome_status(
    content: str,
    title: str = "",
    attempts_list: list | None = None,
    explicit_status: str = ""
) -> str:
    """
    Menentukan outcome status secara obyektif berdasarkan bukti nyata:
    - Jika eksplisit diberikan, gunakan status tersebut.
    - Jika ada attempts yang semuanya FAILED tanpa RESOLVED -> FAILURE.
    - Jika ada kata kunci kegagalan eksplisit tanpa bukti resolusi -> FAILURE.
    - Jika ada bukti empiris penyelesaian/sukses -> SUCCESS.
    - Selain itu -> UNKNOWN (mencegah bias sukses 100%).
    """
    if explicit_status and explicit_status.strip().upper() not in ["", "AUTO", "DEFAULT", "UNKNOWN"]:
        return explicit_status.strip().upper()

    combined = f"{title} {content}".lower()

    if attempts_list:
        statuses = [str(a.get("status", "")).upper() for a in attempts_list if isinstance(a, dict)]
        if statuses and all(s in ["FAILED", "FAILURE"] for s in statuses):
            return "FAILURE"
        if any(s in ["SUCCESS", "RESOLVED"] for s in statuses):
            return "SUCCESS"

    success_indicators = [
        "berhasil", "sukses", "resolved", "lulus uat", "exit code 0",
        "status 200", "fixed", "selesai 100%", "fix confirmed"
    ]
    failure_indicators = [
        "gagal", "error", "crash", "failed", "incident", "exception",
        "timeout", "panic", "terkendala", "broken", "tidak bisa"
    ]

    has_success = any(re.search(r'\b' + re.escape(w) + r'\b', combined) for w in success_indicators)
    has_failure = any(re.search(r'\b' + re.escape(w) + r'\b', combined) for w in failure_indicators)

    if has_failure and not has_success:
        return "FAILURE"
    if has_success and not has_failure:
        return "SUCCESS"
    if has_success and has_failure:
        return "PARTIAL"

    return "UNKNOWN"

@mcp.tool()
def retain(
    content: str,
    bank_id: str = "general",
    category: str = "PROBLEM_SOLVING",
    title: str = "",
    heuristic: str = "",
    decision: str = "",
    attempts: str = "",
    outcome_status: str = "UNKNOWN",
    async_mode: bool = True
) -> str:
    """
    [MemoriaGraph 3.1 Facade] Menyimpan unit memori/pengetahuan/episode ke Memory Bank spesifik.
    Bank: 'infra-sre', 'ai-hud', 'research-personal', 'csirt-security', 'general'.
    Outcome status: 'SUCCESS', 'FAILURE', 'PARTIAL', 'UNKNOWN'.
    Mendukung async background harvesting (Pilar 2) untuk inferensi ultra-cepat.
    """
    if not driver:
        return "Error: Database Neo4j offline."

    # Shared Memory Ingestion Quality Gate
    val = ingestion_gate.validate(
        content=content,
        title=title,
        bank_id=bank_id,
        category=category,
        outcome_status=outcome_status,
        attempts=attempts,
        source_reference="retain-facade"
    )

    if not val.valid:
        return f"🚫 [IngestionGate: {val.status.value}] {', '.join(val.errors)}"

    bank = val.bank
    clean_content = val.sanitized_content
    title = val.sanitized_title
    final_outcome = val.outcome_status

    mgr = EpisodeManager()
    ep = mgr.create_episode(
        title=title,
        category=category,
        objective=clean_content[:150],
        context=bank,
        record_type=val.record_type,
        outcome_applicable=val.outcome_applicable,
        dedupe_fingerprint=val.fingerprint
    )
    ep_id = ep["id"]

    # Beri label bank_id pada Episode di Neo4j
    with driver.session() as s:
        s.run("MATCH (e:Episode {id: $id}) SET e.bank_id = $bank", id=ep_id, bank=bank)

    parsed_attempts = []
    if attempts:
        try:
            parsed_attempts = json.loads(attempts) if isinstance(attempts, str) else attempts
            for att in parsed_attempts:
                mgr.add_attempt(
                    episode_id=ep_id,
                    attempt_number=int(att.get("number", 1)),
                    hypothesis=att.get("hypothesis", ""),
                    action=att.get("action", ""),
                    result=att.get("result", ""),
                    status=att.get("status", "FAILED")
                )
        except Exception as e:
            print(f"Failed to parse attempts: {e}", file=sys.stderr)

    if decision:
        mgr.add_decision(
            episode_id=ep_id,
            choice=decision,
            rationale=heuristic or clean_content[:120]
        )

    mgr.complete_episode(
        episode_id=ep_id,
        outcome_status=final_outcome,
        reflection_lesson=clean_content,
        heuristic=heuristic or clean_content[:120]
    )
    
    with driver.session() as s:
        s.run("""
        MATCH (e:Episode {id: $id})-[:REFLECTED_BY]->(r:Reflection)
        SET r.bank_id = $bank
        """, id=ep_id, bank=bank)

    mgr.close()

    # Pilar 2: Async Background Harvesting
    if recall_engine:
        if async_mode:
            harvester.submit("sync_vector_cache", recall_engine.sync_vector_cache)
        else:
            recall_engine.sync_vector_cache()

    return f"💾 [Retain] Berhasil mencatat memori ke Bank '{bank}' [Type: {val.record_type}, Outcome: {final_outcome}]: '{title}' [ID: {ep_id}]."

@mcp.tool()
def recall(
    query: str,
    limit: int = 5,
    bank_id: str = "",
    mode: str = "hybrid",
    compact: bool = True
) -> str:
    """
    [MemoriaGraph 3.1 Facade] 4-Way Hybrid Recall Engine dengan RRF, Context Isolation, & Result Pruning.
    Mode:
    - 'hybrid': 4-Way BM25 + Graph + Temporal + Vector RRF (Pilar 3: Kompresi Hemat Token).
    - 'context': Graph topic context traversal (pengganti get_context).
    - 'dss': Precedent & decision support (pengganti query_dss).
    - 'beliefs': Cognitive beliefs & heuristics ranking (pengganti list_cognitive_beliefs).
    """
    mode_clean = mode.strip().lower() if mode else "hybrid"

    # Dispatch ke sub-mode jika diminta
    if mode_clean == "context":
        return get_context(query)
    elif mode_clean == "dss":
        return query_dss(situation=query, context=bank_id)
    elif mode_clean == "beliefs":
        return list_cognitive_beliefs(status_filter=bank_id)

    if not recall_engine:
        return "⚠️ Error: Hybrid Recall Engine belum aktif."
    try:
        b_filter = bank_id.strip().lower() if bank_id and bank_id.strip() else None
        results = recall_engine.recall(query, limit=limit, bank_id=b_filter)
        if not results:
            target_str = f" di Bank '{b_filter}'" if b_filter else ""
            return f"Tidak ditemukan memori yang cocok untuk query: '{query}'{target_str}."
        
        bank_header = f" (Memory Bank: `{b_filter}`)" if b_filter else ""

        # Pilar 3: Kompresi Respons & Token Pruning
        if compact:
            lines = [f"🧠 **Hasil 4-Way Hybrid Recall (RRF){bank_header} untuk:** *'{query}'*"]
            for rank, r in enumerate(results, start=1):
                title = r.get("title", "Unnamed")
                lbls = ":".join(r.get("labels", []))
                bid = r.get("bank_id", "general")
                summary = r.get("summary", "").strip()
                if len(summary) > 160:
                    summary = summary[:157] + "..."
                info_part = f" - {summary}" if summary else ""
                lines.append(f"{rank}. **[{bid}] [{lbls}] {title}**{info_part}")
            return "\n".join(lines)
        else:
            lines = [f"🧠 **Hasil 4-Way Hybrid Recall (RRF){bank_header} untuk:** *'{query}'*\n"]
            for rank, r in enumerate(results, start=1):
                title = r.get("title", "Unnamed")
                lbls = ":".join(r.get("labels", []))
                bid = r.get("bank_id", "general")
                rrf = r.get("rrf_score", 0.0)
                channels = ", ".join(r.get("matched_channels", []))
                summary = r.get("summary", "")
                lines.append(f"{rank}. **[{bid}] [{lbls}] {title}** (Score RRF: `{rrf:.4f}`)")
                lines.append(f"   *Channels:* {channels}")
                if summary:
                    short_summary = (summary[:180] + "...") if len(summary) > 180 else summary
                    lines.append(f"   *Info:* {short_summary}")
            return "\n".join(lines)
    except Exception as e:
        return f"? Gagal mengeksekusi recall: {e}"

@mcp.tool()
def reflect(
    question: str = "",
    bank_id: str = "",
    action: str = "reflect",
    target_id: str = "",
    reason: str = ""
) -> str:
    """
    [MemoriaGraph 3.1 Facade] Refleksi kognitif & kalibrasi keyakinan/heuristik.
    Action:
    - 'reflect' (default): Sintesis solusi masa lalu & pola berpikir terkristalisasi.
    - 'reinforce': Memperkuat heuristik/keyakinan (target_id diisi ID/teks keyakinan).
    - 'challenge': Menantang heuristik dengan counter-evidence (target_id & reason).
    - 'dashboard': Mengambil metrik observasi kognitif bulanan.
    """
    act = action.strip().lower() if action else "reflect"

    if act == "reinforce":
        return reinforce_belief_tool(identifier=target_id or question, details=reason)
    elif act == "challenge":
        return challenge_belief_tool(identifier=target_id or question, reason=reason)
    elif act == "dashboard":
        return get_cognitive_dashboard()

    if not driver:
        return "Error: Database Neo4j offline."

    target_bank = bank_id.strip().lower() if bank_id and bank_id.strip() else None

    # 1. Query DSS heuristik relevan
    dss_result = query_personal_dss(question, context=target_bank or "general")

    # 2. Ambil high-confidence patterns dalam bank
    with driver.session() as s:
        cypher = """
        MATCH (p:Pattern)
        WHERE ($bank IS NULL OR coalesce(p.bank_id, 'general') = $bank)
        RETURN p.id AS id, p.rule_statement AS rule, p.confidence_score AS score
        ORDER BY p.confidence_score DESC LIMIT 3
        """
        top_patterns = s.run(cypher, bank=target_bank).data()

    lines = ["🪞 **MEMORIAGRAPH REFLECT: Solusi & Pola Berpikir Masa Lalu**", "--------------------------------------------"]
    if target_bank:
        lines.append(f"🏦 **Memory Bank Terisolasi:** `{target_bank}`")

    if top_patterns:
        lines.append("\n💎 **Crystallized Patterns (Aturan Baku Terbukti):**")
        for p in top_patterns:
            lines.append(f"  - [Score: `{p['score']}`] {p['rule']}")

    heuristics = dss_result.get("relevant_heuristics", [])
    decisions = dss_result.get("observed_decisions", [])
    lessons = dss_result.get("relevant_lessons", [])
    
    if heuristics:
        lines.append("\n💡 **Heuristik Operasional Terkait:**")
        for h in heuristics:
            lines.append(f"  - {h}")

    if decisions:
        lines.append("\n📋 **Keputusan Masa Lalu:**")
        for d in decisions:
            lines.append(f"  - {d}")

    if lessons:
        lines.append("\n📖 **Pelajaran Berharga:**")
        for lesson in lessons:
            lines.append(f"  - {lesson}")

    lines.append("--------------------------------------------")
    return "\n".join(lines)

# ==========================================
# 🔗 BACKWARD-COMPATIBILITY ALIASES (100% FAIL-SAFE)
# ==========================================

@mcp.tool()
def record_cognitive_episode(
    title: str,
    category: str = "PROBLEM_SOLVING",
    objective: str = "",
    context: str = "general",
    problem_description: str = "",
    problem_severity: str = "MEDIUM",
    attempts: str = "",
    decision_choice: str = "",
    decision_rationale: str = "",
    outcome_status: str = "SUCCESS",
    reflection_heuristic: str = ""
) -> str:
    """[Legacy Compatibility] Mencatat episode kognitif lengkap."""
    return retain(
        content=f"{problem_description}\n{decision_rationale}\n{reflection_heuristic}".strip() or objective,
        bank_id=context,
        category=category,
        title=title,
        heuristic=reflection_heuristic,
        decision=decision_choice,
        attempts=attempts,
        outcome_status=outcome_status,
        async_mode=True
    )

@mcp.tool()
def log_event(
    event_type: str,
    description: str,
    context: str = "general",
    epistemic_class: str = "FACT"
) -> str:
    """[Legacy Compatibility] Mencatat event tunggal ke event stream."""
    try:
        ev = log_raw_event(
            event_type=event_type,
            description=description,
            context=context,
            epistemic_class=epistemic_class
        )
        return f"? Event '{event_type}' [{ev['epistemic_class']}] berhasil dicatat: {ev['event_id']}"
    except Exception as err:
        return f"? Gagal mencatat event: {err}"

@mcp.tool()
def query_dss(situation: str, category: str = "", context: str = "") -> str:
    """[Legacy Compatibility] Meminta bantuan Personal Decision Support System (DSS)."""
    try:
        cat_arg = category if category and category.strip() else None
        ctx_arg = context if context and context.strip() else None
        res = query_personal_dss(situation, category=cat_arg, context=ctx_arg)
        outcomes = res["historical_outcomes"]
        decisions = res["observed_decisions"]
        heuristics = res["relevant_heuristics"]
        lessons = res.get("relevant_lessons", [])
        episodes = res.get("matched_episodes", [])

        lines = [
            f"🛡️ **PERSONAL DSS REPORT: {situation}**",
            f"? Kasus Serupa Ditemukan: {res['matched_episodes_count']} episode ({res.get('matched_by', 'KEYWORD')})",
            f"📊 Rekam Jejak Hasil: {outcomes['success']} Sukses | {outcomes['partial']} Parsial | {outcomes['failed']} Gagal",
        ]
        if episodes:
            lines.append("\n📜 **Episode Historis Terkait:**")
            for ep in episodes:
                lines.append(f"  - [{ep['id']}] {ep['title']} ({ep.get('category', '')})")
                if ep.get("objective"):
                    lines.append(f"    Tujuan: {ep['objective']}")

        if decisions:
            lines.append("\n📋 **Keputusan yang Pernah Diambil:**")
            for d in decisions:
                lines.append(f"  - {d}")
        if heuristics:
            lines.append("\n💡 **Heuristik/Pelajaran Masa Lalu:**")
            for h in heuristics:
                lines.append(f"  - {h}")
        if lessons:
            lines.append("\n🔮 **Refleksi & Insight:**")
            for lesson in lessons:
                lines.append(f"  - {lesson}")

        lines.append(f"\nℹ️ *Catatan: {res['disclaimer']}*")
        return "\n".join(lines)
    except Exception as err:
        return f"❌ Gagal query DSS: {err}"

@mcp.tool()
def get_cognitive_dashboard() -> str:
    """[Legacy Compatibility] Mengambil metrik analitik proses kognitif bulanan."""
    try:
        m = get_cognitive_metrics()
        constraints = m["top_decision_constraints"]
        c_lines = ", ".join([f"{c['constraint_name']} ({c['frequency']}x)" for c in constraints]) if constraints else "Belum cukup data"
        exp = m["exploration_pipeline"]

        report = f"""
📊 **PERSONAL COGNITIVE OBSERVATION DASHBOARD**
--------------------------------------------
• Total Episode Terekam    : {m['total_episodes']} episode
• Tingkat Keberhasilan Solusi: {m['success_rate_percent']}%
• Rata-rata Percobaan/Masalah: {m['avg_attempts_per_problem']} attempts
• Faktor Keputusan Dominan  : {c_lines}
• Exploration Pipeline      : {exp['curiosity_count']} Rasa Penasaran -> {exp['prototype_count']} Prototype -> {exp['graduated_projects']} Project Jadi
--------------------------------------------
*Data dihitung otomatis secara induktif dari histori empiris Neo4j.*
"""
        return report.strip()
    except Exception as err:
        return f"? Gagal mengambil metrik kognitif: {err}"

@mcp.tool()
def reinforce_belief_tool(identifier: str, details: str = "") -> str:
    """[Legacy Compatibility] Memperkuat heuristik/keyakinan kognitif."""
    from src.belief_revision import reinforce_belief
    if not driver:
        return "Error: Database Neo4j offline."
    res = reinforce_belief(driver, identifier=identifier, details=details)
    if res["status"] == "SUCCESS":
        c_msg = " 💎 (Terkristalisasi menjadi Pattern!)" if res.get("crystallized") else ""
        return f"✅ Keyakinan '{res['id']}' diperkuat! Score: {res['previous_score']} -> {res['new_score']} (Evidence: {res['evidence_count']}, Status: {res['belief_status']}){c_msg}"
    return f"✅ {res.get('message', 'Gagal memperkuat keyakinan.')}"

@mcp.tool()
def challenge_belief_tool(identifier: str, reason: str = "") -> str:
    """[Legacy Compatibility] Menantang heuristik/keyakinan kognitif."""
    from src.belief_revision import challenge_belief
    if not driver:
        return "Error: Database Neo4j offline."
    res = challenge_belief(driver, identifier=identifier, failure_reason=reason)
    if res["status"] == "CHALLENGED":
        return f"⚠️ Keyakinan '{res['id']}' ditantang! Score: {res['previous_score']} -> {res['new_score']} (Counter-evidence: {res['counter_evidence_count']}, Status: {res['belief_status']}). Alasan: {reason}"
    return f"❌ {res.get('message', 'Gagal menantang keyakinan.')}"

@mcp.tool()
def list_cognitive_beliefs(status_filter: str = "") -> str:
    """[Legacy Compatibility] Mengambil daftar heuristik & keyakinan kognitif."""
    from src.belief_revision import list_beliefs
    if not driver:
        return "Error: Database Neo4j offline."
    filt = status_filter.strip().upper() if status_filter.strip() else None
    beliefs = list_beliefs(driver, status_filter=filt, limit=20)
    if not beliefs:
        return f"Tidak ada keyakinan kognitif dengan filter '{status_filter}'."
    
    lines = [f"📚 **MEMORIAGRAPH BELIEF INDEX ({len(beliefs)} Heuristik):**", "--------------------------------------------"]
    for b in beliefs:
        lines.append(f"• **[{b['status']}]** (Score: `{b['confidence_score']}`, E:{b['evidence_count']}, C:{b['counter_evidence_count']})")
        lines.append(f"  Heuristik: {b['text']}")
    lines.append("--------------------------------------------")
    return "\n".join(lines)

@mcp.tool()
def add_entity(name: str, entity_type: str, description: str = "") -> str:
    """[Legacy Compatibility] Menambahkan entitas generik ke dalam MemoriaGraph."""
    if not driver:
        return "Error: Tidak terhubung ke Neo4j."
    clean_desc = sanitize_data(description)
    query = """
    MERGE (n:Entity {name: $name})
    SET n.type = $type, n.description = $description, n.updated_at = datetime()
    RETURN n.name AS name
    """
    with driver.session() as session:
        session.run(query, name=name, type=entity_type, description=clean_desc)
        return f"Berhasil: Entitas '{name}' (Tipe: {entity_type}) telah disimpan di MemoriaGraph."

@mcp.tool()
def add_relation(source_name: str, target_name: str, relationship: str) -> str:
    """[Legacy Compatibility] Menghubungkan dua entitas dengan relasi."""
    if not driver:
        return "Error: Tidak terhubung ke Neo4j."
    relationship = relationship.upper().replace(" ", "_")
    query = f"""
    MATCH (a:Entity {{name: $source}})
    MATCH (b:Entity {{name: $target}})
    MERGE (a)-[r:`{relationship}`]->(b)
    RETURN type(r)
    """
    with driver.session() as session:
        result = session.run(query, source=source_name, target=target_name)
        if result.peek() is None:
             return "Error: Gagal membuat relasi. Pastikan entitas sudah dibuat sebelumnya."
        return f"Berhasil: Relasi [{source_name}] --({relationship})--> [{target_name}] telah dicatat."

@mcp.tool()
def record_code_action(
    episode_id: str,
    action_description: str,
    repo_path: str = "/home/maskii/Private-key",
    base_ref: str = ""
) -> str:
    """[Legacy Compatibility] Mencatat Action ke dalam Episode lengkap dengan Git Blast-Radius."""
    from src.blast_radius import record_code_action_with_blast_radius
    if not driver:
        return "Error: Database Neo4j offline."
    res = record_code_action_with_blast_radius(
        episode_id=episode_id,
        action_description=action_description,
        repo_path=repo_path,
        base_ref=base_ref or None
    )
    b = res["blast_radius"]
    return f"🚀 [Action] Berhasil dicatat [ID: {res['action_id']}]. Blast Severity: {b.get('blast_severity')}, Files Changed: {b.get('total_files_changed')}, Affected Areas: {', '.join(b.get('affected_areas', []))}."

@mcp.tool()
def get_context(topic: str) -> str:
    """[Legacy Compatibility] Mengambil konteks memori di sekitar sebuah topik."""
    if not driver:
        return "Error: Tidak terhubung ke Neo4j."
        
    import re
    clean_topic = re.sub(r'[^a-zA-Z0-9\s]', ' ', topic.lower())
    stop_words = {"dan", "yang", "untuk", "dengan", "ini", "itu", "pada", "dari", "ke", "di", "the", "and", "for", "with", "coba", "cek", "tolong"}
    terms = [w.strip() for w in clean_topic.split() if len(w.strip()) >= 3 and w.strip() not in stop_words]

    lines = []

    if recall_engine:
        try:
            hits = recall_engine.recall(topic, limit=5)
            if hits:
                lines.append("🧠 **Top Memory Matches (4-Way Hybrid Recall RRF):**")
                for h in hits:
                    lbls = ":".join(h.get("labels", []))
                    lines.append(f"  - **[{lbls}] {h['title']}** (Score: `{h['rrf_score']:.4f}`)")
                lines.append("")
        except Exception as e:
            print(f"Hybrid recall in get_context error: {e}", file=sys.stderr)

    with driver.session() as session:
        q_ent = """
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS toLower($topic)
           OR any(t IN $terms WHERE toLower(n.name) CONTAINS t OR toLower(coalesce(n.description, '')) CONTAINS t)
        OPTIONAL MATCH (n)-[r]-(connected)
        RETURN n.name AS name, n.type AS type, n.description AS description, type(r) AS relation, connected.name AS target_name
        ORDER BY coalesce(n.updated_at, datetime({year: 1970})) DESC
        LIMIT 10
        """
        res_ent = session.run(q_ent, topic=topic, terms=terms).data()

        q_ep = """
        MATCH (e:Episode)
        WHERE toLower(e.title) CONTAINS toLower($topic)
           OR any(t IN $terms WHERE toLower(e.title) CONTAINS t OR toLower(e.objective) CONTAINS t OR toLower(coalesce(e.context, '')) CONTAINS t)
        OPTIONAL MATCH (e)-[:CONTAINED_DECISION]->(d:Decision)
        OPTIONAL MATCH (e)-[:REFLECTED_BY]->(refl:Reflection)
        RETURN e.id AS id, e.title AS title, e.category AS category, e.objective AS objective,
               d.choice AS decision, refl.heuristic AS heuristic, refl.lesson AS lesson
        LIMIT 4
        """
        res_ep = session.run(q_ep, topic=topic, terms=terms).data()

    entities_seen = {}
    relations = []
    for r in res_ent:
        name = r['name']
        if name not in entities_seen:
            entities_seen[name] = {'type': r['type'], 'description': r['description']}
        if r['relation'] and r['target_name']:
            rel_str = f"[{name}] --({r['relation']})-- [{r['target_name']}]"
            if rel_str not in relations:
                relations.append(rel_str)

    if entities_seen:
        lines.append("🔗 **Entitas Terkait:**")
        for name, data in entities_seen.items():
            lines.append(f"  - **{name}** ({data['type']}): {data['description'][:100] if data['description'] else ''}")
        if relations:
            lines.append("\n🔀 **Relasi Terhubung:**")
            for r in relations[:5]:
                lines.append(f"    {r}")

    if res_ep:
        lines.append("\n📜 **Episode Terkait:**")
        for ep in res_ep:
            lines.append(f"  - **[{ep['id']}] {ep['title']}** ({ep['category']})")
            if ep.get('decision'):
                lines.append(f"    Keputusan: {ep['decision']}")
            if ep.get('heuristic'):
                lines.append(f"    💡 Heuristik: {ep['heuristic']}")

    if not lines:
        return f"Tidak ada ingatan atau episode yang terhubung dengan topik '{topic}' di MemoriaGraph."

    return f"🌐 **Konteks MemoriaGraph untuk '{topic}':**\n" + "\n".join(lines)

# ==========================================
# 🌐 PILAR 4: HTTP SERVICE DAEMON (PORT 8085)
# ==========================================

def start_http_background_server():
    """Menjalankan lightweight HTTP endpoint untuk integrasi 9Router & service eksternal."""
    try:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        import uvicorn

        async def health(request):
            return JSONResponse({
                "status": "healthy",
                "service": "MemoriaGraph 3.1.1",
                "engine": "4-Way Hybrid Recall (RRF)",
                "pid": os.getpid()
            })

        async def http_recall(request):
            q = request.query_params.get("query", "")
            limit = int(request.query_params.get("limit", "5"))
            bank = request.query_params.get("bank", "")
            mode = request.query_params.get("mode", "hybrid")
            compact = request.query_params.get("compact", "true").lower() == "true"
            if not q:
                return JSONResponse({"error": "Missing 'query' parameter"}, status_code=400)
            result = recall(query=q, limit=limit, bank_id=bank, mode=mode, compact=compact)
            return JSONResponse({"query": q, "bank": bank, "result": result})

        async def http_retain(request):
            try:
                body = await request.json()
                content = body.get("content", "")
                bank = body.get("bank_id", "general")
                category = body.get("category", "PROBLEM_SOLVING")
                title = body.get("title", "")
                heuristic = body.get("heuristic", "")
                decision = body.get("decision", "")
                if not content:
                    return JSONResponse({"error": "Missing 'content' parameter"}, status_code=400)
                msg = retain(
                    content=content,
                    bank_id=bank,
                    category=category,
                    title=title,
                    heuristic=heuristic,
                    decision=decision,
                    async_mode=True
                )
                return JSONResponse({"status": "success", "message": msg})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        app = Starlette(routes=[
            Route("/health", health),
            Route("/recall", http_recall),
            Route("/retain", http_retain, methods=["POST"]),
        ])

        config = uvicorn.Config(app, host="127.0.0.1", port=8085, log_level="warning")
        srv = uvicorn.Server(config)
        srv.run()
    except Exception as err:
        print(f"⚠️ [HTTP Server] Port 8085 background server skipped: {err}", file=sys.stderr)

# Boot HTTP server in background thread only if explicitly requested
if os.environ.get("RUN_EMBEDDED_HTTP") == "1":
    http_thread = threading.Thread(target=start_http_background_server, daemon=True, name="MemoriaHttp")
    http_thread.start()

if __name__ == "__main__":
    mcp.run()

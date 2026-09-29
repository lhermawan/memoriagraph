"""
MemoriaGraph 2.0 - Model Context Protocol (MCP) Server
Menyediakan tool kognitif tingkat lanjut: Episode Recording, Event Logging, Personal DSS, dan Cognitive Metrics.
"""
from mcp.server.mcpserver import MCPServer
from neo4j import GraphDatabase
import os
import sys
import json
from dotenv import load_dotenv

from src.sanitizer import sanitize_data
from src.event_logger import log_raw_event
from src.episode_manager import EpisodeManager
from src.dss_engine import query_personal_dss, get_cognitive_metrics
from src.hybrid_recall import HybridRecallEngine

# Load environment variables
load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

mcp = MCPServer("MemoriaGraph")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("MemoriaGraph 2.0 / 3.0: Berhasil terhubung ke database Neo4j!", file=sys.stderr)
except Exception as e:
    print(f"Warning: Tidak bisa terhubung ke Neo4j. Error: {e}", file=sys.stderr)
    driver = None

try:
    recall_engine = HybridRecallEngine(k_rrf=60)
    print("MemoriaGraph 3.0: Hybrid Recall Engine (4-Way RRF) aktif!", file=sys.stderr)
except Exception as e:
    print(f"Warning: Gagal inisialisasi HybridRecallEngine: {e}", file=sys.stderr)
    recall_engine = None

# ==========================================
# TOOL COGNITIVE BARU (MEMORIAGRAPH 2.0)
# ==========================================

@mcp.tool()
def record_cognitive_episode(
    title: str,
    category: str = "PROBLEM_SOLVING",
    objective: str = "",
    context: str = "system",
    problem_description: str = "",
    problem_severity: str = "MEDIUM",
    attempts: str = "[]",
    decision_choice: str = "",
    decision_rationale: str = "",
    outcome_status: str = "SUCCESS",
    reflection_heuristic: str = ""
) -> str:
    """
    Merekam satu episode proses berpikir/problem-solving utuh ke dalam MemoriaGraph 2.0.
    Parameter attempts adalah JSON array string, contoh:
    '[{"number": 1, "hypothesis": "...", "action": "...", "result": "...", "status": "FAILED"}]'
    """
    try:
        mgr = EpisodeManager()
        ep = mgr.create_episode(
            title=title,
            category=category,
            objective=objective,
            context=context
        )
        ep_id = ep["id"]

        if problem_description:
            mgr.add_problem(
                episode_id=ep_id,
                description=problem_description,
                category=category,
                severity=problem_severity
            )

        if attempts:
            try:
                att_list = json.loads(attempts) if isinstance(attempts, str) else attempts
                for att in att_list:
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

        if decision_choice:
            mgr.add_decision(
                episode_id=ep_id,
                choice=decision_choice,
                rationale=decision_rationale
            )

        mgr.complete_episode(
            episode_id=ep_id,
            outcome_status=outcome_status,
            reflection_lesson=reflection_heuristic,
            heuristic=reflection_heuristic
        )
        mgr.close()

        return f"✅ Berhasil mencatat Episode Kognitif: '{title}' [ID: {ep_id}] (Status: {outcome_status})."
    except Exception as err:
        return f"❌ Gagal mencatat episode: {err}"

@mcp.tool()
def log_event(
    event_type: str,
    description: str,
    context: str = "general",
    epistemic_class: str = "FACT"
) -> str:
    """
    Mencatat event tunggal ke append-only event stream dengan label epistemologis (FACT, OBSERVATION, INFERENCE, HYPOTHESIS, AI_GENERATED).
    """
    try:
        ev = log_raw_event(
            event_type=event_type,
            description=description,
            context=context,
            epistemic_class=epistemic_class
        )
        return f"✅ Event '{event_type}' [{ev['epistemic_class']}] berhasil dicatat: {ev['event_id']}"
    except Exception as err:
        return f"❌ Gagal mencatat event: {err}"

@mcp.tool()
def query_dss(situation: str, category: str = "", context: str = "") -> str:
    """
    Meminta bantuan Personal Decision Support System (DSS) untuk mencari bukti historis serupa di masa lalu.
    Mendukung pencarian berbasis kata kunci pintar dan filter kategori/konteks.
    """
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
            f"🧠 **PERSONAL DSS REPORT: {situation}**",
            f"• Kasus Serupa Ditemukan: {res['matched_episodes_count']} episode ({res.get('matched_by', 'KEYWORD')})",
            f"• Rekam Jejak Hasil: {outcomes['success']} Sukses | {outcomes['partial']} Parsial | {outcomes['failed']} Gagal",
        ]
        if episodes:
            lines.append("\n📁 **Episode Historis Terkait:**")
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
            lines.append("\n📖 **Refleksi & Insight:**")
            for l in lessons:
                lines.append(f"  - {l}")

        lines.append(f"\n⚠️ *Catatan: {res['disclaimer']}*")
        return "\n".join(lines)
    except Exception as err:
        return f"❌ Gagal query DSS: {err}"

@mcp.tool()
def get_cognitive_dashboard() -> str:
    """
    Mengambil metrik analitik proses kognitif bulanan (Problem Solving rate, average attempts, dominant constraints, exploration).
    """
    try:
        m = get_cognitive_metrics()
        constraints = m["top_decision_constraints"]
        c_lines = ", ".join([f"{c['constraint_name']} ({c['frequency']}x)" for c in constraints]) if constraints else "Belum cukup data"
        exp = m["exploration_pipeline"]

        report = f"""
🧠 **PERSONAL COGNITIVE OBSERVATION DASHBOARD**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total Episode Terekam    : {m['total_episodes']} episode
• Tingkat Keberhasilan Solusi: {m['success_rate_percent']}%
• Rata-rata Percobaan/Masalah: {m['avg_attempts_per_problem']} attempts
• Faktor Keputusan Dominan  : {c_lines}
• Exploration Pipeline      : {exp['curiosity_count']} Rasa Penasaran ➔ {exp['prototype_count']} Prototype ➔ {exp['graduated_projects']} Project Jadi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*Data dihitung otomatis secara induktif dari histori empiris Neo4j.*
"""
        return report.strip()
    except Exception as err:
        return f"❌ Gagal mengambil metrik kognitif: {err}"

# ==========================================
# TOOL BELIEF REVISION (MEMORIAGRAPH 3.0)
# ==========================================

@mcp.tool()
def reinforce_belief_tool(identifier: str, details: str = "") -> str:
    """
    [MemoriaGraph 3.0] Memperkuat heuristik/keyakinan kognitif berdasarkan bukti empiris sukses baru (Logarithmic Dampening).
    """
    from src.belief_revision import reinforce_belief
    if not driver:
        return "Error: Database Neo4j offline."
    res = reinforce_belief(driver, identifier=identifier, details=details)
    if res["status"] == "SUCCESS":
        c_msg = " 💎 (Terkristalisasi menjadi Pattern!)" if res.get("crystallized") else ""
        return f"✅ Keyakinan '{res['id']}' diperkuat! Score: {res['previous_score']} -> {res['new_score']} (Evidence: {res['evidence_count']}, Status: {res['belief_status']}){c_msg}"
    return f"⚠️ {res.get('message', 'Gagal memperkuat keyakinan.')}"

@mcp.tool()
def challenge_belief_tool(identifier: str, reason: str = "") -> str:
    """
    [MemoriaGraph 3.0] Menantang heuristik/keyakinan kognitif dengan counter-evidence kegagalan (Hysteresis Penalti).
    """
    from src.belief_revision import challenge_belief
    if not driver:
        return "Error: Database Neo4j offline."
    res = challenge_belief(driver, identifier=identifier, failure_reason=reason)
    if res["status"] == "CHALLENGED":
        return f"⚠️ Keyakinan '{res['id']}' ditantang! Score: {res['previous_score']} -> {res['new_score']} (Counter-evidence: {res['counter_evidence_count']}, Status: {res['belief_status']}). Alasan: {reason}"
    return f"⚠️ {res.get('message', 'Gagal menantang keyakinan.')}"

@mcp.tool()
def list_cognitive_beliefs(status_filter: str = "") -> str:
    """
    [MemoriaGraph 3.0] Mengambil daftar heuristik & keyakinan kognitif terurut berdasarkan confidence score.
    Filter opsional: 'HIGH_CONFIDENCE', 'OBSERVED', 'CANDIDATE', 'CONTESTED'.
    """
    from src.belief_revision import list_beliefs
    if not driver:
        return "Error: Database Neo4j offline."
    filt = status_filter.strip().upper() if status_filter.strip() else None
    beliefs = list_beliefs(driver, status_filter=filt, limit=20)
    if not beliefs:
        return f"Tidak ada keyakinan kognitif dengan filter '{status_filter}'."
    
    lines = [f"🧠 **MEMORIAGRAPH BELIEF INDEX ({len(beliefs)} Heuristik):**", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
    for b in beliefs:
        lines.append(f"• **[{b['status']}]** (Score: `{b['confidence_score']}`, E:{b['evidence_count']}, C:{b['counter_evidence_count']})")
        lines.append(f"  Heuristik: {b['text']}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

# ==========================================
# TOOL BACKWARD COMPATIBLE (MEMORIAGRAPH 1.0)
# ==========================================

@mcp.tool()
def add_entity(name: str, entity_type: str, description: str = "") -> str:
    """
    [Legacy 1.0] Menambahkan entitas generik ke dalam MemoriaGraph.
    """
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
    """
    [Legacy 1.0] Menghubungkan dua entitas dengan relasi bertanda huruf kapital.
    """
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
             return f"Error: Gagal membuat relasi. Pastikan entitas sudah dibuat sebelumnya."
        return f"Berhasil: Relasi [{source_name}] --({relationship})--> [{target_name}] telah dicatat."

# ==========================================
# BIOMIMETIC MEMORY FACADE API (HINDSIGHT PILLAR)
# ==========================================

@mcp.tool()
def retain(
    content: str,
    bank_id: str = "general",
    category: str = "PROBLEM_SOLVING",
    title: str = "",
    heuristic: str = ""
) -> str:
    """
    [MemoriaGraph 3.0 Facade] Menyimpan unit memori/pengetahuan baru ke dalam Memory Bank spesifik.
    Pilihan bank_id: 'infra-sre', 'ai-hud', 'research-personal', 'csirt-security', 'general'.
    Otomatis melalui Semantic Anti-Slop Sanitizer & Epistemic Grounding Gate.
    """
    if not driver:
        return "Error: Database Neo4j offline."

    from src.semantic_sanitizer import strip_conversational_fluff
    from src.episode_manager import EpisodeManager

    bank = bank_id.strip().lower() if bank_id else "general"
    clean_content = strip_conversational_fluff(content)

    if not title:
        first_line = clean_content.split("\n")[0].strip()
        title = (first_line[:60] + "...") if len(first_line) > 60 else first_line
        if not title:
            title = f"Memori {category.title()} ({bank})"

    mgr = EpisodeManager()
    ep = mgr.create_episode(
        title=title,
        category=category,
        objective=clean_content[:150],
        context=bank
    )
    ep_id = ep["id"]

    # Beri label bank_id pada Episode di Neo4j
    with driver.session() as s:
        s.run("MATCH (e:Episode {id: $id}) SET e.bank_id = $bank", id=ep_id, bank=bank)

    mgr.complete_episode(
        episode_id=ep_id,
        outcome_status="SUCCESS",
        reflection_lesson=clean_content,
        heuristic=heuristic or clean_content[:120]
    )
    
    with driver.session() as s:
        s.run("""
        MATCH (e:Episode {id: $id})-[:REFLECTED_BY]->(r:Reflection)
        SET r.bank_id = $bank
        """, id=ep_id, bank=bank)

    mgr.close()

    if recall_engine:
        recall_engine.sync_vector_cache()

    return f"💾 [Retain] Berhasil mencatat memori ke Bank '{bank}': '{title}' [ID: {ep_id}]."

@mcp.tool()
def recall(query: str, limit: int = 10, bank_id: str = "") -> str:
    """
    [MemoriaGraph 3.0 Facade] 4-Way Hybrid Recall Engine dengan Reciprocal Rank Fusion (RRF) & Context Isolation.
    Mencari memori lintas BM25 Fulltext, Graph Multi-Hop, Temporal Window, dan Dense Vector (Int8 Lokal).
    Filter bank_id opsional: 'infra-sre', 'ai-hud', 'research-personal', 'csirt-security'.
    """
    if not recall_engine:
        return "⚠️ Error: Hybrid Recall Engine belum aktif."
    try:
        b_filter = bank_id.strip().lower() if bank_id and bank_id.strip() else None
        results = recall_engine.recall(query, limit=limit, bank_id=b_filter)
        if not results:
            target_str = f" di Bank '{b_filter}'" if b_filter else ""
            return f"Tidak ditemukan memori yang cocok untuk query: '{query}'{target_str}."
        
        bank_header = f" (Memory Bank: `{b_filter}`)" if b_filter else " (Semua Bank)"
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
        return f"❌ Gagal mengeksekusi recall: {e}"

@mcp.tool()
def reflect(
    question: str,
    bank_id: str = ""
) -> str:
    """
    [MemoriaGraph 3.0 Facade] Melakukan refleksi kognitif mendalam berdasarkan heuristik & crystallized patterns masa lalu.
    Dapat dibatasi ke bank_id tertentu ('infra-sre', 'ai-hud', 'research-personal', 'csirt-security') atau lintas bank.
    """
    if not driver:
        return "Error: Database Neo4j offline."

    from src.dss_engine import query_personal_dss

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

    lines = [f"🪞 **MEMORIAGRAPH REFLECT: Solusi & Pola Berpikir Masa Lalu**", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
    if target_bank:
        lines.append(f"📁 **Memory Bank Terisolasi:** `{target_bank}`")

    if top_patterns:
        lines.append("\n💎 **Crystallized Patterns (Aturan Baku Terbukti):**")
        for p in top_patterns:
            lines.append(f"  • [Score: `{p['score']}`] {p['rule']}")

    heuristics = dss_result.get("relevant_heuristics", [])
    decisions = dss_result.get("observed_decisions", [])
    lessons = dss_result.get("relevant_lessons", [])
    
    if heuristics:
        lines.append("\n💡 **Heuristik Operasional Terkait:**")
        for h in heuristics:
            lines.append(f"  • {h}")

    if decisions:
        lines.append("\n📋 **Keputusan Masa Lalu:**")
        for d in decisions:
            lines.append(f"  • {d}")

    if lessons:
        lines.append("\n📖 **Pelajaran Berharga:**")
        for l in lessons:
            lines.append(f"  • {l}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

@mcp.tool()
def record_code_action(
    episode_id: str,
    action_description: str,
    repo_path: str = "/home/maskii/Private-key",
    base_ref: str = ""
) -> str:
    """
    [MemoriaGraph 3.0] Mencatat Action ke dalam Episode lengkap dengan deteksi Git Blast-Radius otomatis.
    """
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
    """
    Mengambil konteks memori di sekitar sebuah topik (mencakup Entity, Episode, Curiosity, Prototype, dan Heuristik).
    Didukung oleh 4-Way Hybrid Recall Engine (BM25 + Graph + Temporal + Vector RRF).
    """
    if not driver:
        return "Error: Tidak terhubung ke Neo4j."
        
    import re
    clean_topic = re.sub(r'[^a-zA-Z0-9\s]', ' ', topic.lower())
    stop_words = {"dan", "yang", "untuk", "dengan", "ini", "itu", "pada", "dari", "ke", "di", "the", "and", "for", "with", "coba", "cek", "tolong"}
    terms = [w.strip() for w in clean_topic.split() if len(w.strip()) >= 3 and w.strip() not in stop_words]

    lines = []

    # 0. Eksekusi 4-Way Hybrid Recall (RRF) untuk menjamin akurasi & relevansi
    if recall_engine:
        try:
            hits = recall_engine.recall(topic, limit=5)
            if hits:
                lines.append("🧠 **Top Memory Matches (4-Way Hybrid Recall RRF):**")
                for h in hits:
                    lbls = ":".join(h.get("labels", []))
                    channels = ", ".join(h.get("matched_channels", []))
                    lines.append(f"  • **[{lbls}] {h['title']}** (Score: `{h['rrf_score']:.4f}`)")
                    lines.append(f"    *Channels:* {channels}")
                lines.append("")
        except Exception as e:
            print(f"Hybrid recall in get_context error: {e}", file=sys.stderr)

    with driver.session() as session:
        # 1. Search Entities & Relationships
        q_ent = """
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS toLower($topic)
           OR any(t IN $terms WHERE toLower(n.name) CONTAINS t OR toLower(coalesce(n.description, '')) CONTAINS t)
        OPTIONAL MATCH (n)-[r]-(connected)
        RETURN n.name AS name, n.type AS type, n.description AS description, type(r) AS relation, connected.name AS target_name
        ORDER BY coalesce(n.updated_at, datetime({year: 1970})) DESC
        LIMIT 20
        """
        res_ent = session.run(q_ent, topic=topic, terms=terms).data()

        # 2. Search Episodes, Decisions, Reflections
        q_ep = """
        MATCH (e:Episode)
        WHERE toLower(e.title) CONTAINS toLower($topic)
           OR any(t IN $terms WHERE toLower(e.title) CONTAINS t OR toLower(e.objective) CONTAINS t OR toLower(coalesce(e.context, '')) CONTAINS t)
        OPTIONAL MATCH (e)-[:CONTAINED_DECISION]->(d:Decision)
        OPTIONAL MATCH (e)-[:REFLECTED_BY]->(refl:Reflection)
        OPTIONAL MATCH (e)-[:PRODUCED_OUTCOME]->(o:Outcome)
        RETURN e.id AS id, e.title AS title, e.category AS category, e.objective AS objective, e.context AS context,
               d.choice AS decision, refl.heuristic AS heuristic, refl.lesson AS lesson, o.status AS outcome
        LIMIT 5
        """
        res_ep = session.run(q_ep, topic=topic, terms=terms).data()

        # 3. Search Curiosity & Prototypes
        q_cur = """
        MATCH (c:Curiosity)
        WHERE toLower(c.topic) CONTAINS toLower($topic)
           OR any(t IN $terms WHERE toLower(c.topic) CONTAINS t)
        OPTIONAL MATCH (c)-[:TESTED_VIA]->()-[:PROTOTYPED_TO]->(p:Prototype)
        RETURN c.id AS curiosity_id, c.topic AS curiosity_topic, p.id AS prototype_id, p.name AS prototype_name
        LIMIT 5
        """
        res_cur = session.run(q_cur, topic=topic, terms=terms).data()

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
        lines.append("📌 **Entitas Terkait:**")
        for name, data in entities_seen.items():
            lines.append(f"  • **{name}** (Tipe: {data['type']})")
            if data['description']:
                lines.append(f"    Deskripsi: {data['description']}")
        if relations:
            lines.append("\n🔗 **Relasi Terhubung:**")
            for r in relations[:10]:
                lines.append(f"    {r}")

    episodes_seen = {}
    for r in res_ep:
        ep_id = r['id']
        if ep_id not in episodes_seen:
            episodes_seen[ep_id] = r

    if episodes_seen:
        lines.append("\n📁 **Episode & Rencana Terkait:**")
        for ep_id, ep in episodes_seen.items():
            lines.append(f"  • **[{ep_id}] {ep['title']}** ({ep['category']})")
            if ep.get('objective'):
                lines.append(f"    Tujuan: {ep['objective']}")
            if ep.get('decision'):
                lines.append(f"    Keputusan: {ep['decision']}")
            if ep.get('heuristic'):
                lines.append(f"    💡 Heuristik: {ep['heuristic']}")
            if ep.get('lesson'):
                lines.append(f"    📖 Lesson: {ep['lesson']}")

    if res_cur:
        lines.append("\n🚀 **Exploration & Prototype:**")
        for c in res_cur:
            lines.append(f"  • Ide: {c['curiosity_topic']}")
            if c.get('prototype_name'):
                lines.append(f"    Prototipe: {c['prototype_name']}")

    if not lines:
        return f"Tidak ada ingatan atau episode yang terhubung dengan topik '{topic}' di MemoriaGraph."

    return f"🧠 **Konteks MemoriaGraph untuk '{topic}':**\n" + "\n".join(lines)

if __name__ == "__main__":
    mcp.run()

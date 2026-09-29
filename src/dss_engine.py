"""
MemoriaGraph 2.0 - Personal Decision Support System (DSS) & Cognitive Analytics Engine
Menyediakan pencarian bukti historis obyektif (Historical Retrieval & Evidence Matching).
"""
import os
from typing import Dict, Any, List, Optional
import dotenv
from neo4j import GraphDatabase

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def query_personal_dss(
    situation_description: str,
    category: Optional[str] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mencari kesamaan historis di MemoriaGraph dan menyajikan bukti keputusan masa lalu.
    Prioritas:
    1. Pencarian kata kunci (keyword search) pada title, objective, context.
    2. Fallback ke category/context jika ditentukan secara eksplisit.
    """
    import re
    driver = get_driver()
    
    clean_sit = re.sub(r'[^a-zA-Z0-9\s]', ' ', situation_description.lower())
    stop_words = {"dan", "yang", "untuk", "dengan", "ini", "itu", "pada", "dari", "ke", "di", "the", "and", "for", "with", "coba", "cek", "tolong"}
    terms = [w.strip() for w in clean_sit.split() if len(w.strip()) >= 3 and w.strip() not in stop_words]

    keyword_query = """
    MATCH (e:Episode)
    WHERE any(t IN $terms WHERE 
        toLower(e.title) CONTAINS t OR 
        toLower(e.objective) CONTAINS t OR 
        toLower(coalesce(e.context, '')) CONTAINS t
    )
    OPTIONAL MATCH (e)-[:CONTAINED_DECISION]->(d:Decision)
    OPTIONAL MATCH (d)-[r:WEIGHTED_BY]->(c:Constraint)
    OPTIONAL MATCH (e)-[:PRODUCED_OUTCOME]->(o:Outcome)
    OPTIONAL MATCH (e)-[:REFLECTED_BY]->(refl:Reflection)
    RETURN 
        e.id AS episode_id,
        e.title AS title,
        e.category AS category,
        e.objective AS objective,
        e.context AS context,
        d.choice AS decision,
        d.rationale AS rationale,
        c.category AS dominant_constraint,
        o.status AS outcome,
        refl.heuristic AS heuristic,
        refl.lesson AS lesson
    ORDER BY e.timestamp_start DESC
    LIMIT 10
    """

    results = []
    matched_by = "NONE"

    with driver.session() as s:
        if terms:
            results = s.run(keyword_query, terms=terms).data()
            if results:
                matched_by = "KEYWORD"

        # Fallback jika tidak ada keyword match tapi ada category/context eksplisit
        if not results and (context or (category and category.upper() not in ["ALL", "PROBLEM_SOLVING", ""])):
            cat_filter = category.upper() if category else None
            fallback_query = """
            MATCH (e:Episode)
            WHERE ($cat_filter IS NULL OR e.category = $cat_filter)
              AND ($context IS NULL OR e.context = $context)
            OPTIONAL MATCH (e)-[:CONTAINED_DECISION]->(d:Decision)
            OPTIONAL MATCH (d)-[r:WEIGHTED_BY]->(c:Constraint)
            OPTIONAL MATCH (e)-[:PRODUCED_OUTCOME]->(o:Outcome)
            OPTIONAL MATCH (e)-[:REFLECTED_BY]->(refl:Reflection)
            RETURN 
                e.id AS episode_id,
                e.title AS title,
                e.category AS category,
                e.objective AS objective,
                e.context AS context,
                d.choice AS decision,
                d.rationale AS rationale,
                c.category AS dominant_constraint,
                o.status AS outcome,
                refl.heuristic AS heuristic,
                refl.lesson AS lesson
            ORDER BY e.timestamp_start DESC
            LIMIT 10
            """
            results = s.run(fallback_query, cat_filter=cat_filter, context=context).data()
            if results:
                matched_by = "CATEGORY_FALLBACK"

    driver.close()

    total_matches = len(results)
    success_count = sum(1 for r in results if r.get("outcome") == "SUCCESS")
    failed_count = sum(1 for r in results if r.get("outcome") == "FAILED")
    partial_count = sum(1 for r in results if r.get("outcome") == "PARTIAL_SUCCESS")

    episodes_list = []
    seen_ep = set()
    for r in results:
        ep_id = r["episode_id"]
        if ep_id not in seen_ep:
            seen_ep.add(ep_id)
            episodes_list.append({
                "id": ep_id,
                "title": r.get("title", ""),
                "category": r.get("category", ""),
                "objective": r.get("objective", ""),
                "outcome": r.get("outcome", "RESOLVED")
            })

    common_decisions = list(dict.fromkeys([r["decision"] for r in results if r.get("decision")]))
    heuristics = list(dict.fromkeys([r["heuristic"] for r in results if r.get("heuristic")]))
    lessons = list(dict.fromkeys([r["lesson"] for r in results if r.get("lesson")]))

    disclaimer = "This is historical evidence, not an automated command or recommendation."
    if matched_by == "CATEGORY_FALLBACK":
        disclaimer += f" (Catatan: Tidak ditemukan kecocokan kata kunci langsung. Menampilkan histori kategori '{category}')."
    elif matched_by == "NONE":
        disclaimer = "Tidak ditemukan episode historis yang cocok dengan kata kunci situasi ini."

    return {
        "current_situation": situation_description,
        "matched_by": matched_by,
        "matched_episodes_count": len(episodes_list),
        "matched_episodes": episodes_list,
        "historical_outcomes": {
            "success": success_count,
            "partial": partial_count,
            "failed": failed_count
        },
        "observed_decisions": common_decisions[:5],
        "relevant_heuristics": heuristics[:5],
        "relevant_lessons": lessons[:5],
        "disclaimer": disclaimer
    }

def get_cognitive_metrics() -> Dict[str, Any]:
    """
    Menghitung metrik kognitif observasional untuk evaluasi berkala (bulanan).
    """
    driver = get_driver()
    
    with driver.session() as s:
        # 1. Total Episode & Outcome
        ep_stats = s.run("""
        MATCH (e:Episode)
        OPTIONAL MATCH (e)-[:PRODUCED_OUTCOME]->(o:Outcome)
        RETURN 
            count(e) AS total_episodes,
            sum(CASE WHEN o.status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_episodes
        """).single()

        # 2. Average Attempts per Episode
        att_stats = s.run("""
        MATCH (e:Episode)-[:HAS_ATTEMPT]->(a:Attempt)
        WITH e, count(a) AS att_count
        RETURN avg(att_count) AS avg_attempts
        """).single()

        # 3. Decision Constraints Distribution
        constraints_stats = s.run("""
        MATCH (d:Decision)-[r:WEIGHTED_BY]->(c:Constraint)
        RETURN c.category AS constraint_name, count(d) AS frequency
        ORDER BY frequency DESC
        LIMIT 5
        """).data()

        # 4. Exploration to Project Progression
        curiosity_stats = s.run("""
        MATCH (c:Curiosity)
        OPTIONAL MATCH (c)-[:TESTED_VIA]->()-[:PROTOTYPED_TO]->(p:Prototype)
        OPTIONAL MATCH (p)-[:GRADUATED_TO]->(proj:Project)
        RETURN 
            count(DISTINCT c) AS total_curiosity,
            count(DISTINCT p) AS total_prototypes,
            count(DISTINCT proj) AS total_graduated_projects
        """).single()

    driver.close()

    total_ep = ep_stats["total_episodes"] if ep_stats else 0
    succ_ep = ep_stats["success_episodes"] if ep_stats else 0
    succ_rate = round((succ_ep / total_ep * 100), 1) if total_ep > 0 else 0.0

    avg_att = round(att_stats["avg_attempts"], 2) if (att_stats and att_stats["avg_attempts"]) else 1.0

    return {
        "total_episodes": total_ep,
        "success_rate_percent": succ_rate,
        "avg_attempts_per_problem": avg_att,
        "top_decision_constraints": constraints_stats,
        "exploration_pipeline": {
            "curiosity_count": curiosity_stats["total_curiosity"] if curiosity_stats else 0,
            "prototype_count": curiosity_stats["total_prototypes"] if curiosity_stats else 0,
            "graduated_projects": curiosity_stats["total_graduated_projects"] if curiosity_stats else 0
        }
    }

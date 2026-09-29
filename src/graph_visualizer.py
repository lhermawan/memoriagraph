"""
MemoriaGraph 3.0 - 3D Holographic Graph Bridge (Friday HUD & Three.js WebGL)
Mengekspor struktur graf kognitif (nodes & links) ke format yang kompatibel dengan Three.js / Force-Graph 3D.
Menyediakan pewarnaan cluster biomimetic bank:
- ai-hud           : #00f0ff (Cyan Arc Reactor)
- infra-sre        : #00ff88 (Emerald SRE)
- csirt-security   : #ff0055 (Crimson Security)
- research-personal: #b000ff (Purple Curiosity)
- general          : #ffaa00 (Amber Core)
"""

import os
import sys
import dotenv
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

BANK_COLORS = {
    "ai-hud": "#00f0ff",
    "infra-sre": "#00ff88",
    "csirt-security": "#ff0055",
    "research-personal": "#b000ff",
    "general": "#ffaa00",
}

LABEL_WEIGHTS = {
    "Project": 10,
    "Episode": 8,
    "Pattern": 7,
    "Decision": 6,
    "Problem": 5,
    "Reflection": 5,
    "Curiosity": 4,
    "Prototype": 4,
    "Entity": 3,
    "Action": 2,
    "Outcome": 2,
}

def export_graph_for_3d_hud(limit_nodes: int = 150, bank_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Mengambil data graf dari Neo4j dan memformatnya menjadi skema 3D Three.js.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as s:
        # 1. Ambil simpul (Nodes)
        node_query = """
        MATCH (n)
        WHERE (n:Entity OR n:Episode OR n:Problem OR n:Decision OR n:Reflection OR n:Pattern OR n:Curiosity OR n:Prototype OR n:Project)
          AND ($bank IS NULL OR coalesce(n.bank_id, 'general') = $bank)
        RETURN 
            elementId(n) AS id,
            labels(n)[0] AS primary_label,
            coalesce(n.title, n.name, n.id, 'Unnamed') AS name,
            coalesce(n.bank_id, 'general') AS bank,
            coalesce(n.confidence_score, 0.7) AS confidence,
            coalesce(n.status, 'ACTIVE') AS status
        LIMIT $limit
        """
        raw_nodes = s.run(node_query, limit=limit_nodes, bank=bank_filter).data()
        node_ids = {n["id"] for n in raw_nodes}
        
        # 2. Ambil relasi (Links) antar simpul yang terpilih
        link_query = """
        MATCH (a)-[r]->(b)
        WHERE elementId(a) IN $ids AND elementId(b) IN $ids
        RETURN 
            elementId(a) AS source,
            elementId(b) AS target,
            type(r) AS type
        LIMIT 300
        """
        raw_links = s.run(link_query, ids=list(node_ids)).data()

    driver.close()

    # Format nodes
    formatted_nodes = []
    for n in raw_nodes:
        bank = n.get("bank", "general")
        lbl = n.get("primary_label", "Entity")
        weight = LABEL_WEIGHTS.get(lbl, 3)
        
        formatted_nodes.append({
            "id": n["id"],
            "name": n["name"][:50],
            "full_name": n["name"],
            "label": lbl,
            "bank": bank,
            "color": BANK_COLORS.get(bank, "#ffaa00"),
            "val": weight,
            "confidence": n.get("confidence", 0.7),
            "status": n.get("status", "ACTIVE")
        })

    # Format links
    formatted_links = []
    for l in raw_links:
        formatted_links.append({
            "source": l["source"],
            "target": l["target"],
            "type": l["type"]
        })

    return {
        "ok": True,
        "total_nodes": len(formatted_nodes),
        "total_links": len(formatted_links),
        "bank_filter": bank_filter or "all",
        "clusters": list(BANK_COLORS.keys()),
        "nodes": formatted_nodes,
        "links": formatted_links
    }

if __name__ == "__main__":
    data = export_graph_for_3d_hud(limit_nodes=20)
    print(f"Nodes: {data['total_nodes']}, Links: {data['total_links']}")
    print("Sample Node:", data["nodes"][0] if data["nodes"] else "None")

"""
MemoriaGraph 2.0 - Record Log Bridge
Menerima payload log dari AI-SRE hub, melakukan sanitasi rahasia, mencatat ke event stream, dan menghubungkan ke Neo4j.
"""
import json
import os
import sys

import dotenv
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from src.event_logger import log_raw_event
from src.sanitizer import sanitize_data

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

try:
    raw_data = json.load(sys.stdin)
    data = sanitize_data(raw_data)
    
    name = data.get("entityName")
    etype = data.get("entityType", "PatrolLog")
    desc = data.get("description", "")
    relations = data.get("relations", [])

    # 1. Catat ke Event Stream
    log_raw_event(
        event_type="patrol" if "Patrol" in etype else "alert",
        description=f"[{etype}] {name}: {desc[:100]}...",
        context="sre-watchdog",
        source="ai-sre-hub",
        epistemic_class="OBSERVED",
        sync_to_graph=False
    )

    # 2. Rekam ke Neo4j
    with driver.session() as s:
        s.run("""
        MERGE (n:Entity {name: $name})
        SET n.type = $type, n.description = $description, n.timestamp = datetime()
        """, name=name, type=etype, description=desc)

        for r in relations:
            rel_type = r.get("relationship", "CONNECTED_TO").upper().replace(" ", "_")
            target = r.get("target")
            if target:
                q = f"MATCH (a:Entity {{name: $source}}) MERGE (b:Entity {{name: $target}}) MERGE (a)-[rel:`{rel_type}`]->(b)"
                s.run(q, source=name, target=target)

    driver.close()
    print("SUCCESS_RECORD_MEMORIAGRAPH")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

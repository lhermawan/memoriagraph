"""
MemoriaGraph 2.0 - Event Logger Engine
Menyimpan event mentah ke append-only JSONL stream dan memproyeksikannya ke Neo4j.
"""
import os
import json
import uuid
import datetime
from typing import Dict, Any, Optional
import dotenv
from neo4j import GraphDatabase
from src.sanitizer import sanitize_data
from src.semantic_sanitizer import strip_conversational_fluff, classify_epistemic_grounding

dotenv.load_dotenv("/opt/memoriagraph/.env")

EVENTS_DIR = "/opt/memoriagraph/events"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

os.makedirs(EVENTS_DIR, exist_ok=True)

# Validasi Epistemic Taxonomy
VALID_EPISTEMIC_CLASSES = {"FACT", "OBSERVATION", "INFERENCE", "HYPOTHESIS", "AI_GENERATED"}
VALID_EVENT_TYPES = {
    "question", "observation", "search", "discovery", "problem",
    "hypothesis", "experiment", "decision", "action", "failure",
    "success", "reflection", "idea", "project", "patrol", "alert"
}

def get_event_logfile() -> str:
    month_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")
    return os.path.join(EVENTS_DIR, f"{month_str}.jsonl")

def log_raw_event(
    event_type: str,
    description: str,
    context: str = "general",
    episode_id: Optional[str] = None,
    source: str = "system",
    confidence: float = 1.0,
    epistemic_class: str = "FACT",
    metadata: Optional[Dict[str, Any]] = None,
    sync_to_graph: bool = True
) -> Dict[str, Any]:
    """
    Mencatat event ke file stream lokal dan sinkronisasi ke Neo4j.
    Dilengkapi Anti-Slop: Pembersihan basa-basi dan verifikasi grounding empiris.
    """
    event_type = event_type.lower()
    if event_type not in VALID_EVENT_TYPES:
        event_type = "observation"

    clean_desc = strip_conversational_fluff(description)

    # Epistemic Grounding Quality Gate
    verified_class, ground_conf = classify_epistemic_grounding(clean_desc, claimed_status=epistemic_class)
    final_epistemic = verified_class if verified_class in VALID_EPISTEMIC_CLASSES else epistemic_class.upper()
    final_conf = min(confidence, ground_conf)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    event_id = f"EVT-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    event_payload = {
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": now_iso,
        "episode_id": episode_id,
        "context": context,
        "description": clean_desc,
        "source": source,
        "confidence": final_conf,
        "epistemic_class": final_epistemic,
        "metadata": metadata or {}
    }

    # 1. Sanitasi Rahasia
    sanitized_event = sanitize_data(event_payload)

    # 2. Append-Only Local Storage
    logfile = get_event_logfile()
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(sanitized_event) + "\n")

    # 3. Proyeksikan ke Neo4j jika diminta
    if sync_to_graph:
        _project_event_to_graph(sanitized_event)

    return sanitized_event

def _project_event_to_graph(event: Dict[str, Any]):
    """Proyeksikan event ke node Neo4j dengan label epistemik ganda."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        epistemic_label = event["epistemic_class"].capitalize()
        query = f"""
        MERGE (e:Event:{epistemic_label} {{id: $id}})
        SET e.event_type = $event_type,
            e.description = $description,
            e.context = $context,
            e.source = $source,
            e.confidence = $confidence,
            e.timestamp = datetime($timestamp),
            e.epistemic_class = $epistemic_class
        WITH e
        MATCH (p:Person {{name: 'Maskii'}})
        MERGE (p)-[:EXPERIENCED]->(e)
        """
        with driver.session() as s:
            s.run(query,
                  id=event["event_id"],
                  event_type=event["event_type"],
                  description=event["description"],
                  context=event["context"],
                  source=event["source"],
                  confidence=event["confidence"],
                  timestamp=event["timestamp"],
                  epistemic_class=event["epistemic_class"])
            
            # Jika ada episode_id, hubungkan ke episode
            if event.get("episode_id"):
                s.run("""
                MATCH (ev:Event {id: $event_id})
                MATCH (ep:Episode {id: $episode_id})
                MERGE (ep)-[:CONTAINS_EVENT]->(ev)
                """, event_id=event["event_id"], episode_id=event["episode_id"])
                
        driver.close()
    except Exception as err:
        print(f"⚠️ [EventLogger] Gagal sinkron ke Neo4j: {err}")

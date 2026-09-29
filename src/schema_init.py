"""
MemoriaGraph 2.0 - Schema Initializer & Migration
Mengonfigurasi constraints dan indexes di Neo4j untuk integritas & performa graph kognitif.
"""
import os
import sys
if "/opt/memoriagraph" not in sys.path:
    sys.path.insert(0, "/opt/memoriagraph")
import dotenv
from neo4j import GraphDatabase

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

CONSTRAINTS = [
    ("Episode_id", "CREATE CONSTRAINT episode_id_unique IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE"),
    ("Problem_id", "CREATE CONSTRAINT problem_id_unique IF NOT EXISTS FOR (p:Problem) REQUIRE p.id IS UNIQUE"),
    ("Decision_id", "CREATE CONSTRAINT decision_id_unique IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE"),
    ("Action_id", "CREATE CONSTRAINT action_id_unique IF NOT EXISTS FOR (a:Action) REQUIRE a.id IS UNIQUE"),
    ("Outcome_id", "CREATE CONSTRAINT outcome_id_unique IF NOT EXISTS FOR (o:Outcome) REQUIRE o.id IS UNIQUE"),
    ("Reflection_id", "CREATE CONSTRAINT reflection_id_unique IF NOT EXISTS FOR (r:Reflection) REQUIRE r.id IS UNIQUE"),
    ("Pattern_id", "CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS FOR (pat:Pattern) REQUIRE pat.id IS UNIQUE"),
    ("Event_id", "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (ev:Event) REQUIRE ev.id IS UNIQUE"),
    ("Constraint_id", "CREATE CONSTRAINT constraint_id_unique IF NOT EXISTS FOR (c:Constraint) REQUIRE c.id IS UNIQUE"),
    ("Person_name", "CREATE CONSTRAINT person_name_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE"),
]

INDEXES = [
    ("Episode_category", "CREATE INDEX episode_category_idx IF NOT EXISTS FOR (e:Episode) ON (e.category)"),
    ("Episode_timestamp", "CREATE INDEX episode_time_idx IF NOT EXISTS FOR (e:Episode) ON (e.timestamp_start)"),
    ("Problem_category", "CREATE INDEX problem_cat_idx IF NOT EXISTS FOR (p:Problem) ON (p.category)"),
    ("Decision_time", "CREATE INDEX decision_time_idx IF NOT EXISTS FOR (d:Decision) ON (d.timestamp)"),
    ("Event_type", "CREATE INDEX event_type_idx IF NOT EXISTS FOR (ev:Event) ON (ev.event_type)"),
    ("Event_time", "CREATE INDEX event_time_idx IF NOT EXISTS FOR (ev:Event) ON (ev.timestamp)"),
    ("Reflection_status", "CREATE INDEX reflection_status_idx IF NOT EXISTS FOR (r:Reflection) ON (r.status)"),
    ("Reflection_conf", "CREATE INDEX reflection_conf_idx IF NOT EXISTS FOR (r:Reflection) ON (r.confidence_score)"),
    ("Pattern_status", "CREATE INDEX pattern_status_idx IF NOT EXISTS FOR (pat:Pattern) ON (pat.status)"),
    ("Pattern_conf", "CREATE INDEX pattern_conf_idx IF NOT EXISTS FOR (pat:Pattern) ON (pat.confidence_score)"),
    ("Entity_bank", "CREATE INDEX entity_bank_idx IF NOT EXISTS FOR (n:Entity) ON (n.bank_id)"),
    ("Episode_bank", "CREATE INDEX episode_bank_idx IF NOT EXISTS FOR (e:Episode) ON (e.bank_id)"),
    ("Problem_bank", "CREATE INDEX problem_bank_idx IF NOT EXISTS FOR (p:Problem) ON (p.bank_id)"),
    ("Decision_bank", "CREATE INDEX decision_bank_idx IF NOT EXISTS FOR (d:Decision) ON (d.bank_id)"),
    ("Reflection_bank", "CREATE INDEX reflection_bank_idx IF NOT EXISTS FOR (r:Reflection) ON (r.bank_id)"),
    ("Pattern_bank", "CREATE INDEX pattern_bank_idx IF NOT EXISTS FOR (pat:Pattern) ON (pat.bank_id)"),
    ("Cognitive_fulltext", """
        CREATE FULLTEXT INDEX cognitive_fulltext_idx IF NOT EXISTS
        FOR (n:Entity|Episode|Problem|Decision|Action|Outcome|Reflection|Pattern|Fact|Curiosity|Prototype|Project)
        ON EACH [n.name, n.title, n.description, n.heuristic, n.objective, n.rationale, n.rule_statement]
    """),
]

def migrate_memory_banks(session):
    print("  🏦 Menjalankan partisi Biomimetic Memory Banks (bank_id)...")
    session.run("""
    MATCH (n)
    WHERE (n:Episode OR n:Entity OR n:Problem OR n:Decision OR n:Reflection OR n:Pattern OR n:Curiosity OR n:Prototype OR n:Project)
      AND (toLower(coalesce(n.title, '')) =~ '.*(hud|hologram|three\\\\.js|arc reactor|webgl|voice).*'
        OR toLower(coalesce(n.name, '')) =~ '.*(hud|hologram|three\\\\.js|arc reactor|webgl|voice).*'
        OR toLower(coalesce(n.description, '')) =~ '.*(hud|hologram|three\\\\.js|arc reactor|webgl|voice).*')
    SET n.bank_id = 'ai-hud'
    """)

    session.run("""
    MATCH (n)
    WHERE (n:Episode OR n:Entity OR n:Problem OR n:Decision OR n:Reflection OR n:Pattern)
      AND (toLower(coalesce(n.title, '')) =~ '.*(strix|pentest|kali|cve|exploit|csirt|security).*'
        OR toLower(coalesce(n.name, '')) =~ '.*(strix|pentest|kali|cve|exploit|csirt|security).*')
    SET n.bank_id = 'csirt-security'
    """)

    session.run("""
    MATCH (n)
    WHERE (n:Episode OR n:Entity OR n:Problem OR n:Decision OR n:Reflection OR n:Pattern OR n:Curiosity OR n:Prototype OR n:Project)
      AND (toLower(coalesce(n.title, '')) =~ '.*(clipper|youtube|kimi|memoriagraph).*'
        OR toLower(coalesce(n.name, '')) =~ '.*(clipper|youtube|kimi|memoriagraph).*')
      AND n.bank_id IS NULL
    SET n.bank_id = 'research-personal'
    """)

    session.run("""
    MATCH (n)
    WHERE (n:Episode OR n:Entity OR n:Problem OR n:Decision OR n:Reflection OR n:Pattern)
      AND (toLower(coalesce(n.title, '')) =~ '.*(pm2|watchdog|lucky|atcs|vm-maskii|sre|patrol|ram|memory leak|tailscale).*'
        OR toLower(coalesce(n.name, '')) =~ '.*(pm2|watchdog|lucky|atcs|vm-maskii|sre|patrol|ram|memory leak|tailscale).*')
      AND n.bank_id IS NULL
    SET n.bank_id = 'infra-sre'
    """)

    session.run("""
    MATCH (n)
    WHERE (n:Episode OR n:Entity OR n:Problem OR n:Decision OR n:Reflection OR n:Pattern OR n:Curiosity OR n:Prototype OR n:Project)
      AND n.bank_id IS NULL
    SET n.bank_id = 'general'
    """)
    print("  ✅ Partisi memory bank selesai diaplikasikan ke seluruh simpul graph.")

def init_schema():
    from src.belief_revision import migrate_existing_beliefs
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("🚀 [MemoriaGraph 2.0 / 3.0] Menginisialisasi Skema Database Neo4j...")
    
    with driver.session() as session:
        # Terapkan Constraints
        for name, query in CONSTRAINTS:
            try:
                session.run(query)
                print(f"  ✅ Constraint '{name}' aktif.")
            except Exception as e:
                print(f"  ⚠️ Gagal membuat constraint '{name}': {e}")
                
        # Terapkan Indexes
        for name, query in INDEXES:
            try:
                session.run(query)
                print(f"  ✅ Index '{name}' aktif.")
            except Exception as e:
                print(f"  ⚠️ Gagal membuat index '{name}': {e}")
                
        # Pastikan node Person Maskii sudah ada
        session.run("""
        MERGE (p:Person {name: 'Maskii'})
        ON CREATE SET p.id = 'maskii', p.created_at = datetime()
        """)
        print("  👤 Node Person 'Maskii' terverifikasi.")

        # Jalankan partisi Biomimetic Memory Banks
        migrate_memory_banks(session)

    # Jalankan migrasi data beliefs
    migrate_existing_beliefs(driver)
        
    driver.close()
    print("✨ [MemoriaGraph 2.0 / 3.0] Skema Neo4j berhasil dikonfigurasi!")

if __name__ == "__main__":
    init_schema()

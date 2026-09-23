from mcp.server.mcpserver import MCPServer
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Konfigurasi Koneksi Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Inisialisasi Server MCP
mcp = MCPServer("MemoriaGraph")

# Inisialisasi Driver Neo4j
try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("MemoriaGraph: Berhasil terhubung ke database Neo4j!")
except Exception as e:
    print(f"Warning: Tidak bisa terhubung ke Neo4j. Error: {e}")
    driver = None

@mcp.tool()
def add_entity(name: str, entity_type: str, description: str = "") -> str:
    """
    Menambahkan sebuah Entitas (Node) baru ke dalam MemoriaGraph.
    Gunakan ini untuk mencatat subjek, objek, atau konsep baru.
    """
    if not driver:
        return "Error: Tidak terhubung ke Neo4j."
    
    query = """
    MERGE (n:Entity {name: $name})
    SET n.type = $type, n.description = $description
    RETURN n.name AS name
    """
    with driver.session() as session:
        session.run(query, name=name, type=entity_type, description=description)
        return f"Berhasil: Entitas '{name}' (Tipe: {entity_type}) telah disimpan di MemoriaGraph."

@mcp.tool()
def add_relation(source_name: str, target_name: str, relationship: str) -> str:
    """
    Membuat garis hubung (Relasi) antara dua entitas yang sudah ada.
    Gunakan huruf KAPITAL dan underscore untuk relationship.
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

@mcp.tool()
def get_context(topic: str) -> str:
    """
    Mengambil konteks memori di sekitar sebuah topik.
    """
    if not driver:
        return "Error: Tidak terhubung ke Neo4j."
        
    query = """
    MATCH (n:Entity {name: $topic})-[r]-(connected)
    RETURN n.name AS source, type(r) AS relation, connected.name AS target
    LIMIT 20
    """
    context_data = []
    with driver.session() as session:
        result = session.run(query, topic=topic)
        for record in result:
            context_data.append(f"[{record['source']}] --({record['relation']})-- [{record['target']}]")
            
    if not context_data:
        return f"Tidak ada ingatan yang terhubung dengan topik '{topic}' di MemoriaGraph."
        
    return f"Konteks untuk '{topic}' ditemukan:\n" + "\n".join(context_data)

if __name__ == "__main__":
    mcp.run()

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASS = os.getenv("NEO4J_PASSWORD")

try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASS))
    driver.verify_connectivity()
    print("✅ KONEKSI SUKSES: MemoriaGraph berhasil terhubung ke database Neo4j Desktop!")
except Exception as e:
    print(f"❌ KONEKSI GAGAL: {e}")

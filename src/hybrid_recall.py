"""
MemoriaGraph 3.0 - 4-Way Hybrid Recall Engine with Reciprocal Rank Fusion (RRF)
Mengintegrasikan:
1. BM25 Fulltext Index (Lucene via Neo4j cognitive_fulltext_idx)
2. Multi-Hop Graph Traversal
3. Temporal Window Scoring
4. Dense Vector Semantic Similarity (FastEmbed Int8 Local ONNX, Zero-API-Key + Vector Cache)
Dilebur menggunakan Reciprocal Rank Fusion (RRF, k=60).
"""

import os
import sys
import re
import math
import pickle
import datetime
import time
from typing import Dict, Any, List, Optional, Tuple
import dotenv
import numpy as np
from neo4j import GraphDatabase

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")
VECTOR_CACHE_FILE = "/opt/memoriagraph/.vector_cache.pkl"

# Lazy-loaded singleton FastEmbed model
_EMBED_MODEL = None

def get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from fastembed import TextEmbedding
            _EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        except Exception as e:
            print(f"⚠️ [HybridRecall] FastEmbed tidak dapat dimuat: {e}", file=sys.stderr)
            _EMBED_MODEL = False
    return _EMBED_MODEL if _EMBED_MODEL is not False else None

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def build_lucene_query(raw_query: str) -> str:
    """
    Membersihkan dan membangun Lucene query toleran untuk fulltext index.
    Mendukung token pemecahan tanda hubung, underscore, dan fuzzy matching.
    """
    cleaned = re.sub(r'[\+\-\&\|\!\(\)\{\}\[\]\^\"\~\*\?\:\\\/]', ' ', raw_query)
    tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 1]
    
    if not tokens:
        return "*"
        
    clauses = []
    for t in tokens:
        clauses.append(f"{t}* OR {t}~")
    
    if len(tokens) > 1:
        phrase = " ".join(tokens)
        return f"({ ' OR '.join(clauses) }) OR \"{phrase}\"^2"
    return " OR ".join(clauses)

class HybridRecallEngine:
    def __init__(self, k_rrf: int = 60, auto_sync_vectors: bool = True):
        self.k_rrf = k_rrf
        self.driver = get_driver()
        self.vector_cache: Dict[str, Any] = {} # node_id -> {title, labels, summary, vec, ...}
        self.matrix_node_ids: List[str] = []
        self.vector_matrix: Optional[np.ndarray] = None
        
        self._load_vector_cache()
        if auto_sync_vectors and (not self.vector_cache or len(self.vector_cache) < 100):
            self.sync_vector_cache()

    def close(self):
        if self.driver:
            self.driver.close()

    def _load_vector_cache(self):
        """Memuat cache vektor dari disk jika tersedia."""
        if os.path.exists(VECTOR_CACHE_FILE):
            try:
                with open(VECTOR_CACHE_FILE, "rb") as f:
                    self.vector_cache = pickle.load(f)
                self._rebuild_matrix()
            except Exception as e:
                print(f"⚠️ Gagal memuat vector cache: {e}", file=sys.stderr)
                self.vector_cache = {}

    def _save_vector_cache(self):
        """Menyimpan cache vektor ke disk."""
        try:
            with open(VECTOR_CACHE_FILE, "wb") as f:
                pickle.dump(self.vector_cache, f)
        except Exception as e:
            print(f"⚠️ Gagal menyimpan vector cache: {e}", file=sys.stderr)

    def _rebuild_matrix(self):
        """Membangun matriks numpy untuk perbandingan kosinus instan (<1ms)."""
        if not self.vector_cache:
            self.vector_matrix = None
            self.matrix_node_ids = []
            return
            
        self.matrix_node_ids = list(self.vector_cache.keys())
        vecs = [self.vector_cache[nid]["vector"] for nid in self.matrix_node_ids]
        mat = np.array(vecs, dtype=np.float32)
        # Normalisasi baris
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.vector_matrix = mat / norms

    def sync_vector_cache(self):
        """
        Sinkronisasi embedding node dari Neo4j ke vector cache lokal.
        Hanya meng-embed node baru yang belum ada di cache.
        """
        embedder = get_embed_model()
        if not embedder:
            return

        with self.driver.session() as s:
            nodes = s.run("""
            MATCH (n)
            WHERE n:Entity OR n:Episode OR n:Problem OR n:Decision OR n:Action OR n:Outcome OR n:Reflection OR n:Pattern OR n:Fact OR n:Curiosity OR n:Prototype OR n:Project
            RETURN 
                elementId(n) AS node_id,
                labels(n) AS labels,
                coalesce(n.title, n.name, n.id, 'Unnamed') AS title,
                coalesce(n.description, n.objective, n.rationale, n.heuristic, '') AS summary,
                n.timestamp AS timestamp,
                n.timestamp_start AS timestamp_start,
                n.category AS category,
                coalesce(n.bank_id, 'general') AS bank_id
            """).data()

        # Selalu update properti bank_id jika berubah
        for n in nodes:
            nid = n["node_id"]
            if nid in self.vector_cache:
                self.vector_cache[nid]["bank_id"] = n.get("bank_id", "general")

        new_nodes = [n for n in nodes if n["node_id"] not in self.vector_cache]
        if not new_nodes:
            self._save_vector_cache()
            self._rebuild_matrix()
            return

        texts = [f"{n['title']}. {n['summary']}".strip() for n in new_nodes]
        new_vecs = list(embedder.embed(texts))

        for n, v in zip(new_nodes, new_vecs):
            self.vector_cache[n["node_id"]] = {
                "node_id": n["node_id"],
                "labels": n["labels"],
                "title": n["title"],
                "summary": n["summary"],
                "timestamp": n["timestamp"],
                "timestamp_start": n["timestamp_start"],
                "category": n["category"],
                "bank_id": n.get("bank_id", "general"),
                "vector": np.array(v, dtype=np.float32)
            }

        self._save_vector_cache()
        self._rebuild_matrix()
        print(f"✅ [HybridRecall] Vector cache tersinkronisasi ({len(self.vector_cache)} node aktif).", file=sys.stderr)

    def _channel_bm25(self, session, lucene_query: str, limit: int = 25, bank_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Jalur 1: BM25 Fulltext Search via Neo4j cognitive_fulltext_idx dengan Memory Bank filter."""
        cypher = """
        CALL db.index.fulltext.queryNodes("cognitive_fulltext_idx", $q) YIELD node, score
        WHERE $bank IS NULL OR coalesce(node.bank_id, 'general') = $bank
        RETURN 
            elementId(node) AS node_id,
            labels(node) AS labels,
            coalesce(node.title, node.name, node.id, 'Unnamed') AS title,
            coalesce(node.description, node.objective, node.rationale, node.heuristic, '') AS summary,
            node.timestamp AS timestamp,
            node.timestamp_start AS timestamp_start,
            node.category AS category,
            coalesce(node.bank_id, 'general') AS bank_id,
            score AS bm25_score
        LIMIT $limit
        """
        try:
            return session.run(cypher, q=lucene_query, limit=limit, bank=bank_id).data()
        except Exception as e:
            print(f"⚠️ BM25 Channel error: {e}", file=sys.stderr)
            return []

    def _channel_graph_traversal(self, session, seed_node_ids: List[str], limit: int = 25, bank_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Jalur 2: Multi-Hop Graph Traversal dari node unggulan BM25 dengan Memory Bank filter."""
        if not seed_node_ids:
            return []
            
        cypher = """
        MATCH (seed) WHERE elementId(seed) IN $seed_ids
        MATCH (seed)-[r]-(neighbor)
        WHERE $bank IS NULL OR coalesce(neighbor.bank_id, 'general') = $bank
        WITH neighbor, count(r) AS degree_to_seeds
        RETURN 
            elementId(neighbor) AS node_id,
            labels(neighbor) AS labels,
            coalesce(neighbor.title, neighbor.name, neighbor.id, 'Unnamed') AS title,
            coalesce(neighbor.description, neighbor.objective, neighbor.rationale, neighbor.heuristic, '') AS summary,
            neighbor.timestamp AS timestamp,
            neighbor.timestamp_start AS timestamp_start,
            neighbor.category AS category,
            coalesce(neighbor.bank_id, 'general') AS bank_id,
            degree_to_seeds AS graph_score
        ORDER BY degree_to_seeds DESC
        LIMIT $limit
        """
        try:
            return session.run(cypher, seed_ids=seed_node_ids[:8], limit=limit, bank=bank_id).data()
        except Exception as e:
            print(f"⚠️ Graph Traversal Channel error: {e}", file=sys.stderr)
            return []

    def _channel_temporal(self, session, raw_query: str, limit: int = 25, bank_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Jalur 3: Temporal Window Scoring berdasarkan petunjuk waktu dengan Memory Bank filter."""
        q_lower = raw_query.lower()
        now = datetime.datetime.now()
        target_dates = []
        
        date_matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', q_lower)
        if date_matches:
            target_dates.extend(date_matches)
            
        if "besok" in q_lower or "tomorrow" in q_lower:
            tomorrow = now + datetime.timedelta(days=1)
            target_dates.append(tomorrow.strftime("%Y-%m-%d"))
        if "hari ini" in q_lower or "today" in q_lower:
            target_dates.append(now.strftime("%Y-%m-%d"))
        if "kemarin" in q_lower or "yesterday" in q_lower:
            yesterday = now - datetime.timedelta(days=1)
            target_dates.append(yesterday.strftime("%Y-%m-%d"))
            
        if not target_dates:
            cypher = """
            MATCH (e:Episode)
            WHERE e.timestamp_start IS NOT NULL AND ($bank IS NULL OR coalesce(e.bank_id, 'general') = $bank)
            RETURN 
                elementId(e) AS node_id,
                labels(e) AS labels,
                coalesce(e.title, e.name, e.id, 'Unnamed') AS title,
                coalesce(e.description, e.objective, '') AS summary,
                e.timestamp AS timestamp,
                e.timestamp_start AS timestamp_start,
                e.category AS category,
                coalesce(e.bank_id, 'general') AS bank_id,
                1.0 AS temporal_score
            ORDER BY e.timestamp_start DESC
            LIMIT $limit
            """
            try:
                return session.run(cypher, limit=limit, bank=bank_id).data()
            except Exception:
                return []
                
        cypher = """
        MATCH (n)
        WHERE ($bank IS NULL OR coalesce(n.bank_id, 'general') = $bank) AND any(d IN $dates WHERE 
            toString(n.timestamp_start) CONTAINS d OR 
            toString(n.timestamp) CONTAINS d OR 
            toLower(coalesce(n.title, '')) CONTAINS d OR
            toLower(coalesce(n.name, '')) CONTAINS d
        )
        RETURN 
            elementId(n) AS node_id,
            labels(n) AS labels,
            coalesce(n.title, n.name, n.id, 'Unnamed') AS title,
            coalesce(n.description, n.objective, n.rationale, n.heuristic, '') AS summary,
            n.timestamp AS timestamp,
            n.timestamp_start AS timestamp_start,
            n.category AS category,
            coalesce(n.bank_id, 'general') AS bank_id,
            2.0 AS temporal_score
        LIMIT $limit
        """
        try:
            return session.run(cypher, dates=target_dates, limit=limit, bank=bank_id).data()
        except Exception as e:
            print(f"⚠️ Temporal Channel error: {e}", file=sys.stderr)
            return []

    def _channel_vector(self, query_text: str, limit: int = 25, bank_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Jalur 4: Dense Vector Semantic Similarity via FastEmbed Int8 Lokal + Cache (<8ms) dengan Memory Bank filter."""
        embedder = get_embed_model()
        if not embedder or self.vector_matrix is None or len(self.matrix_node_ids) == 0:
            return []
            
        try:
            # Embed query string saja (hanya 1 string = ~6ms)
            q_vec = list(embedder.embed([query_text]))[0]
            q_arr = np.array(q_vec, dtype=np.float32)
            norm = np.linalg.norm(q_arr)
            if norm > 0:
                q_arr /= norm
                
            # Dot-product matriks instan (<0.3ms)
            sims = np.dot(self.vector_matrix, q_arr)
            
            # Ambil candidate lebih banyak untuk filtering bank
            candidate_k = min(len(self.matrix_node_ids), limit * 4 if bank_id else limit)
            top_k_indices = np.argsort(sims)[-candidate_k:][::-1]
            results = []
            for idx in top_k_indices:
                score = float(sims[idx])
                nid = self.matrix_node_ids[idx]
                info = dict(self.vector_cache[nid])
                if bank_id and info.get("bank_id", "general") != bank_id:
                    continue
                info.pop("vector", None)
                info["vector_score"] = score
                results.append(info)
                if len(results) >= limit:
                    break
                
            return results
        except Exception as e:
            print(f"⚠️ Vector Channel error: {e}", file=sys.stderr)
            return []

    def recall(self, query: str, limit: int = 10, bank_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Eksekusi 4-Way Hybrid Recall dengan Reciprocal Rank Fusion (RRF) & Context Isolation (Memory Bank).
        RRF_Score(d) = sum_{m in M} (1 / (k + rank_m(d)))
        """
        lucene_query = build_lucene_query(query)
        
        with self.driver.session() as session:
            # 1. Jalur BM25
            bm25_results = self._channel_bm25(session, lucene_query, limit=25, bank_id=bank_id)
            seed_ids = [r["node_id"] for r in bm25_results]
            
            # 2. Jalur Graph Multi-hop
            graph_results = self._channel_graph_traversal(session, seed_ids, limit=25, bank_id=bank_id)
            
            # 3. Jalur Temporal
            temporal_results = self._channel_temporal(session, query, limit=25, bank_id=bank_id)
            
            # 4. Jalur Dense Vector (Cepat via Matrix Dot-Product)
            vector_results = self._channel_vector(query, limit=25, bank_id=bank_id)
            
            # ==========================================
            # RECIPROCAL RANK FUSION (RRF)
            # ==========================================
            rrf_scores: Dict[str, float] = {}
            node_data_map: Dict[str, Dict[str, Any]] = {}
            channel_hits: Dict[str, List[str]] = {}
            
            channels = [
                ("BM25", bm25_results),
                ("GRAPH", graph_results),
                ("TEMPORAL", temporal_results),
                ("VECTOR", vector_results),
            ]
            
            for channel_name, res_list in channels:
                for rank_idx, item in enumerate(res_list, start=1):
                    nid = item["node_id"]
                    if nid not in node_data_map:
                        node_data_map[nid] = item
                    if nid not in channel_hits:
                        channel_hits[nid] = []
                    channel_hits[nid].append(f"{channel_name} (rank {rank_idx})")
                    
                    increment = 1.0 / (self.k_rrf + rank_idx)
                    rrf_scores[nid] = rrf_scores.get(nid, 0.0) + increment

            sorted_nids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
            
            final_results = []
            for nid in sorted_nids[:limit]:
                node_info = dict(node_data_map[nid])
                node_info["rrf_score"] = round(rrf_scores[nid], 6)
                node_info["matched_channels"] = channel_hits.get(nid, [])
                final_results.append(node_info)
                
            return final_results

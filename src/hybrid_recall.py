"""
MemoriaGraph 3.0 - 4-Way Hybrid Recall Engine with Reciprocal Rank Fusion (RRF)
Mengintegrasikan:
1. BM25 Fulltext Index (Lucene via Neo4j cognitive_fulltext_idx)
2. Multi-Hop Graph Traversal
3. Temporal Window Scoring
4. Dense Vector Semantic Similarity (FastEmbed Int8 Local ONNX, Zero-API-Key + Vector Cache)
Dilebur menggunakan Reciprocal Rank Fusion (RRF, k=60).
"""

import datetime
import hashlib
import os
import pickle
import re
import sys
import threading
import time
from typing import Any

try:
    from filelock import FileLock, Timeout
except ImportError:
    import contextlib
    @contextlib.contextmanager
    def FileLock(path, timeout=10):
        yield
    class Timeout(Exception):
        pass

import dotenv
import numpy as np
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, VECTOR_CACHE_FILE

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
        self._cache_lock = threading.Lock()
        self.vector_cache: dict[str, Any] = {} # node_id -> {title, labels, summary, fingerprint, vec, ...}
        self.matrix_node_ids: list[str] = []
        self.vector_matrix: np.ndarray | None = None
        
        self._load_vector_cache()
        self._query_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._cache_ttl = 300  # 5 menit (Pilar 5 - LRU Query Cache)
        if auto_sync_vectors and (not self.vector_cache or len(self.vector_cache) < 100):
            self.sync_vector_cache()

    def close(self):
        if self.driver:
            self.driver.close()

    @property
    def _lock_file_path(self) -> str:
        return f"{VECTOR_CACHE_FILE}.lock"

    def _load_vector_cache(self):
        """Memuat cache vektor dari disk secara aman dengan cross-process lock, validasi checksum, dan auto-recovery jika korup."""
        with self._cache_lock:
            if os.path.exists(VECTOR_CACHE_FILE):
                lock_path = self._lock_file_path
                try:
                    with FileLock(lock_path, timeout=10):
                        with open(VECTOR_CACHE_FILE, "rb") as f:
                            raw = pickle.load(f)
                    if isinstance(raw, dict) and raw.get("schema_version") == 2 and "data" in raw:
                        if "checksum" in raw:
                            data_bytes = pickle.dumps(raw["data"], protocol=pickle.HIGHEST_PROTOCOL)
                            expected_checksum = hashlib.sha256(data_bytes).hexdigest()
                            if raw["checksum"] != expected_checksum:
                                raise ValueError(f"Envelope checksum mismatch: {raw['checksum']} vs {expected_checksum}")
                        self.vector_cache = raw["data"]
                    elif isinstance(raw, dict):
                        # Kompatibilitas mundur dengan raw dict v1
                        self.vector_cache = raw
                    else:
                        raise ValueError("Format cache vektor tidak valid atau tidak dikenali.")
                    self._rebuild_matrix()
                except Exception as e:
                    print(f"⚠️ Gagal memuat vector cache: {e}. Mengisolasi cache rusak & menjadwalkan recovery...", file=sys.stderr)
                    corrupt_path = f"{VECTOR_CACHE_FILE}.corrupted.{int(time.time())}"
                    try:
                        with FileLock(lock_path, timeout=5):
                            if os.path.exists(VECTOR_CACHE_FILE):
                                os.rename(VECTOR_CACHE_FILE, corrupt_path)
                                print(f"📦 Cache rusak diisolasi ke: {corrupt_path}", file=sys.stderr)
                    except Exception as rename_err:
                        print(f"⚠️ Gagal mengisolasi cache rusak: {rename_err}", file=sys.stderr)
                    self.vector_cache = {}
                    self._rebuild_matrix()

    def _save_vector_cache(self):
        """
        Menyimpan cache vektor ke disk secara ATOMIK (write to tmp -> flush -> fsync -> atomic replace).
        Menyertakan amplop metadata versi, SHA-256 checksum, dan koordinasi lintas proses (FileLock).
        """
        with self._cache_lock:
            cache_dir = os.path.dirname(os.path.abspath(VECTOR_CACHE_FILE)) or "."
            os.makedirs(cache_dir, exist_ok=True)
            lock_path = self._lock_file_path
            temp_path = f"{VECTOR_CACHE_FILE}.tmp.{os.getpid()}.{threading.get_ident()}"

            data_bytes = pickle.dumps(self.vector_cache, protocol=pickle.HIGHEST_PROTOCOL)
            checksum = hashlib.sha256(data_bytes).hexdigest()
            envelope = {
                "schema_version": 2,
                "model": "BAAI/bge-small-en-v1.5",
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "node_count": len(self.vector_cache),
                "checksum": checksum,
                "data": self.vector_cache
            }
            try:
                with open(temp_path, "wb") as f:
                    pickle.dump(envelope, f, protocol=pickle.HIGHEST_PROTOCOL)
                    f.flush()
                    os.fsync(f.fileno())
                with FileLock(lock_path, timeout=15):
                    os.replace(temp_path, VECTOR_CACHE_FILE)
            except Timeout:
                print(f"⚠️ [HybridRecall] Timeout ({lock_path}) saat menyimpan vector cache!", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ Gagal menyimpan vector cache secara atomik: {e}", file=sys.stderr)
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

    def _rebuild_matrix(self):
        """Membangun matriks numpy untuk perbandingan kosinus instan (<1ms)."""
        if not self.vector_cache:
            self.vector_matrix = None
            self.matrix_node_ids = []
            return
            
        self.matrix_node_ids = list(self.vector_cache.keys())
        vecs = [self.vector_cache[nid]["vector"] for nid in self.matrix_node_ids if "vector" in self.vector_cache[nid]]
        if not vecs:
            self.vector_matrix = None
            self.matrix_node_ids = []
            return
        mat = np.array(vecs, dtype=np.float32)
        # Normalisasi baris
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.vector_matrix = mat / norms

    @staticmethod
    def _compute_fingerprint(title: str, summary: str) -> str:
        content_bytes = f"{title.strip()}|{summary.strip()}".encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()[:16]

    def sync_vector_cache(self):
        """
        Sinkronisasi embedding node dari Neo4j ke vector cache lokal.
        Fitur Keandalan (Audit P0-2):
        1. Pruning stale nodes: Hapus node di cache yang sudah dihapus dari Neo4j.
        2. Invalidation update: Re-embed jika judul atau ringkasan node berubah (via fingerprint).
        3. Atomic persistence: Menyimpan state bersih via atomic replace.
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

        live_node_ids = {n["node_id"] for n in nodes}
        cache_modified = False

        # 1. Prune deleted / stale nodes
        stale_ids = [nid for nid in list(self.vector_cache.keys()) if nid not in live_node_ids]
        if stale_ids:
            for sid in stale_ids:
                del self.vector_cache[sid]
            cache_modified = True
            print(f"🧹 [HybridRecall] {len(stale_ids)} stale/deleted nodes dipangkas dari cache.", file=sys.stderr)

        # 2. Periksa update bank_id dan fingerprint
        nodes_to_embed = []
        for n in nodes:
            nid = n["node_id"]
            title = n["title"]
            summary = n["summary"]
            fp = self._compute_fingerprint(title, summary)
            n["fingerprint"] = fp

            if nid in self.vector_cache:
                cached_entry = self.vector_cache[nid]
                if cached_entry.get("bank_id") != n.get("bank_id", "general"):
                    cached_entry["bank_id"] = n.get("bank_id", "general")
                    cache_modified = True
                # Jika sudah punya vektor valid tapi belum ada fingerprint (migrasi dari v1):
                # Backfill fingerprint tanpa re-embedding seluruh graf!
                if "vector" in cached_entry and cached_entry.get("fingerprint") is None:
                    cached_entry["fingerprint"] = fp
                    cache_modified = True
                elif cached_entry.get("fingerprint") != fp:
                    nodes_to_embed.append(n)
            else:
                nodes_to_embed.append(n)

        # 3. Lakukan embedding untuk node baru atau yang berubah
        if nodes_to_embed:
            texts = [f"{n['title']}. {n['summary']}".strip() for n in nodes_to_embed]
            new_vecs = list(embedder.embed(texts))

            for n, v in zip(nodes_to_embed, new_vecs):
                self.vector_cache[n["node_id"]] = {
                    "node_id": n["node_id"],
                    "labels": n["labels"],
                    "title": n["title"],
                    "summary": n["summary"],
                    "timestamp": n["timestamp"],
                    "timestamp_start": n["timestamp_start"],
                    "category": n["category"],
                    "bank_id": n.get("bank_id", "general"),
                    "fingerprint": n["fingerprint"],
                    "vector": np.array(v, dtype=np.float32)
                }
            cache_modified = True

        if cache_modified:
            self._save_vector_cache()
            self._rebuild_matrix()
            if hasattr(self, "_query_cache"):
                self._query_cache.clear()
            print(f"✅ [HybridRecall] Vector cache tersinkronisasi ({len(self.vector_cache)} node aktif).", file=sys.stderr)

    def _channel_bm25(self, session, lucene_query: str, limit: int = 25, bank_id: str | None = None) -> list[dict[str, Any]]:
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

    def _channel_graph_traversal(self, session, seed_node_ids: list[str], limit: int = 25, bank_id: str | None = None) -> list[dict[str, Any]]:
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

    def _channel_temporal(self, session, raw_query: str, limit: int = 25, bank_id: str | None = None) -> list[dict[str, Any]]:
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

        recency_keywords = ["terbaru", "recent", "latest", "terkini", "terakhir"]
        has_recency_intent = any(rw in q_lower for rw in recency_keywords)
            
        if not target_dates and not has_recency_intent:
            # PENTING (Audit P1-1): Jika tidak ada petunjuk tanggal dan tidak ada intensi 'terbaru',
            # JANGAN suntikkan 25 episode acak ke RRF! Kembalikan [] agar RRF dipimpin oleh
            # BM25, Graph Traversal, dan Dense Vector Semantic Similarity secara obyektif.
            return []

        if not target_dates and has_recency_intent:
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

    def _channel_vector(self, query_text: str, limit: int = 25, bank_id: str | None = None) -> list[dict[str, Any]]:
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

    def recall(self, query: str, limit: int = 10, bank_id: str | None = None) -> list[dict[str, Any]]:
        """
        Eksekusi 4-Way Hybrid Recall dengan Reciprocal Rank Fusion (RRF) & Context Isolation (Memory Bank).
        RRF_Score(d) = sum_{m in M} (1 / (k + rank_m(d)))
        """
        cache_key = f"{bank_id or 'all'}:{limit}:{query.strip().lower()}"
        if hasattr(self, "_query_cache") and cache_key in self._query_cache:
            ts, cached_res = self._query_cache[cache_key]
            if (datetime.datetime.now().timestamp() - ts) < self._cache_ttl:
                return cached_res

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
            rrf_scores: dict[str, float] = {}
            node_data_map: dict[str, dict[str, Any]] = {}
            channel_hits: dict[str, list[str]] = {}
            
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

            if hasattr(self, "_query_cache"):
                if len(self._query_cache) > 256:
                    oldest = min(self._query_cache.keys(), key=lambda k: self._query_cache[k][0])
                    del self._query_cache[oldest]
                self._query_cache[cache_key] = (datetime.datetime.now().timestamp(), final_results)
                
            return final_results

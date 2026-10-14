# ⚡ 4-Way Hybrid Recall Engine

**MemoriaGraph 3.1** implements a **4-Way Reciprocal Rank Fusion (RRF)** retrieval engine that achieves both high precision and broad semantic recall in under 150ms, boosted by in-memory LRU caching and async background vectorization.

---

## 🔬 The Four Retrieval Lanes

### 1. BM25 Lucene Fulltext Index (`weight: 1.0`)
- **Engine**: Neo4j Fulltext Index `cognitive_fulltext_idx`.
- **Target Fields**: `name`, `description`, `objective`, `rule_statement`, `heuristic`, `title`.
- **Pre-processing**: Query tokenization with Lucene wildcard expansion (`term*`) and fuzzy matching (`term~1`).
- **Strength**: Exact keyword matching for error codes, server hostnames, package names, and CLI commands.

### 2. Multi-hop Graph Traversal (`weight: 0.8`)
- **Engine**: Cypher 2-hop neighborhood expansion.
- **Pattern**: `MATCH (n)-[r*1..2]-(m) WHERE ...`
- **Strength**: Uncovers indirect relationships (e.g. an incident on node `web-server-01` caused by a configuration change in `nginx-ingress`).

### 3. Temporal Window Filtering (`weight: 0.6`)
- **Engine**: Exponential decay formula on event timestamps:
  $$S_{temporal} = e^{-\lambda \cdot \Delta t}$$
- **Strength**: Prioritizes fresh incidents and recent code actions while down-weighting obsolete data.

### 4. Quantized Int8 Dense Vector Embeddings (`weight: 1.2`)
- **Engine**: `FastEmbed` ONNX Runtime with quantized Int8 model (`BAAI/bge-small-en-v1.5`, 384 dimensions).
- **Execution**: Local CPU matrix multiplication with zero external API latency, zero cost, and asynchronous background ingestion.
- **Strength**: Conceptual and semantic similarity (e.g. matching "memory exhaustion" with "OOM killed").

---

## 🧮 Reciprocal Rank Fusion (RRF) Formula

All candidates from the four lanes are scored and merged using RRF ($k=60$):

$$RRF(d) = \sum_{m \in M} w_m \cdot \frac{1}{k + r_m(d)}$$

Where:
- $M \in \{\text{BM25}, \text{Graph}, \text{Temporal}, \text{Vector}\}$
- $w_m$ is the lane-specific weight
- $r_m(d)$ is the 1-based rank of item $d$ in lane $m$
- $k = 60$ is the standard smoothing parameter preventing top ranks from dominating

---

## 🚀 Performance Optimizations in Version 3.1

### 1. In-Memory LRU Cache (<1 ms)
- An in-memory cache stores hot query embeddings and merged RRF candidates for 300 seconds (5-minute TTL).
- Repeated queries bypass Neo4j and vector re-computation entirely, returning in `< 1 ms`.

### 2. Async Background Vector Harvester (<30 ms write)
- Ingestion (`retain()`) writes the episode/fact directly to Neo4j in `< 30 ms`.
- Vector embeddings are calculated in a background worker thread (`harvester.py`), decoupling CPU matrix operations from request latency.

### 3. Compact Result Pruning (65% Token Savings)
- Instead of returning verbose raw graph properties and multi-channel rank dumps, results are pruned into clean, compact representations containing only the entity title, labels, RRF score, and essential heuristic/solution.

---

## 📈 Latency Profile
- In-Memory Cached Query: **< 1 ms**
- Cold 4-Way Fusion Query: **~128 ms**
- Neo4j Cypher Execution: **~35 ms**
- Asynchronous Ingestion (`retain`): **< 30 ms**

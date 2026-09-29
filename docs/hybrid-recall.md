# ⚡ 4-Way Hybrid Recall Engine

MemoriaGraph 3.0 implements a **4-Way Reciprocal Rank Fusion (RRF)** retrieval engine that achieves both high precision and broad semantic recall in under 150ms.

---

## 🔬 The Four Retrieval Lanes

### 1. BM25 Lucene Fulltext Index (`weight: 1.0`)
- **Engine**: Neo4j Fulltext Index `cognitive_fulltext_idx`.
- **Target Fields**: `name`, `description`, `objective`, `rule_statement`, `heuristic`, `title`.
- **Pre-processing**: Query tokenization with Lucene wildcard expansion (`term*`) and fuzzy matching (`term~1`).
- **Strength**: Exact keyword matching for error codes, server IPs, package names, and commands.

### 2. Multi-hop Graph Traversal (`weight: 0.8`)
- **Engine**: Cypher 2-hop neighborhood expansion.
- **Pattern**: `MATCH (n)-[r*1..2]-(m) WHERE ...`
- **Strength**: Uncovers indirect relationships (e.g. an incident on node `lucky` caused by a configuration change in `nginx`).

### 3. Temporal Window Filtering (`weight: 0.6`)
- **Engine**: Exponential decay formula on event timestamps:
  $$S_{temporal} = e^{-\lambda \cdot \Delta t}$$
- **Strength**: Prioritizes fresh incidents and recent code actions while down-weighting obsolete data.

### 4. Quantized Int8 Dense Vector Embeddings (`weight: 1.2`)
- **Engine**: `FastEmbed` ONNX Runtime with quantized Int8 model (`BAAI/bge-small-en-v1.5`, 384 dimensions).
- **Execution**: Local CPU matrix multiplication with zero external API latency and zero cost.
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

## 📈 Latency Profile
- Single query latency: **~138 ms**
- Memory cache dot-product: **< 1 ms**
- Neo4j query latency: **~40 ms**

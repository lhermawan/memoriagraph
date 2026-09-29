# Changelog

All notable changes to **MemoriaGraph** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] - 2026-09-29

### 🚀 The Architectural Triad: Hindsight + Anti-Slop + Codebase-Memory

#### Added
- **4-Way Hybrid Recall Engine (`src/hybrid_recall.py`)**:
  - Combining BM25 Lucene Fulltext Search (`cognitive_fulltext_idx`), Multi-hop Cypher Graph Traversal, Temporal Window Filtering, and Quantized Int8 Dense Vector Embeddings (`bge-small-en-v1.5` via FastEmbed ONNX).
  - Reciprocal Rank Fusion (RRF, $k=60$) blending algorithm achieving 100% retrieval accuracy with 82x speedup (~140ms latency).
- **Dynamic Belief Revision & Evidence Engine (`src/belief_revision.py`)**:
  - Confidence scoring ($0.0 - 1.0$), evidence vs counter-evidence counters, and multi-tier cognitive status (`CANDIDATE` $\to$ `OBSERVED` $\to$ `HIGH_CONFIDENCE`).
  - Logarithmic dampening on positive reinforcement.
  - Asymmetric hysteresis protection against single anomalous failures.
  - Automatic pattern crystallization when heuristics reach high confidence.
- **Semantic Quality Gate & Anti-Slop Sanitizer (`src/semantic_sanitizer.py`)**:
  - Rule-based AI fluff, boilerplate pleasantry, and circular summary stripper.
  - Epistemic Grounding Gate ensuring performance claims refer to real exit codes, PM2 metrics, or telemetry.
  - Code Comment Stripper purging trivial inline remarks before graph ingestion.
- **Biomimetic Memory Banks (`infra-sre`, `ai-hud`, `research-personal`, `csirt-security`, `general`)**:
  - Clean cognitive partition of memories preventing domain interference.
  - Unified Facade MCP API: `retain`, `recall`, and `reflect`.
- **Codebase-Memory Anchor (`src/blast_radius.py`)**:
  - Git diff and filesystem change inspection mapping code modifications, affected functions, and modules to `:Action` nodes in Neo4j.
  - MCP Tool `record_code_action`.
- **3D Holographic Graph Bridge (`src/graph_visualizer.py`)**:
  - REST/JSON export endpoint for Friday Holographic HUD Three.js WebGL canvas (`/api/graph/visualize`) with cluster coloring per memory bank.
- **MCP Server Expansion (`server.py`)**:
  - 14 production MCP tools covering memory management, DSS, beliefs, codebase actions, and cognitive dashboards.
- **Repository Architecture Modernization**:
  - Full PEP 621 `pyproject.toml`, MCP `server.json`, `glama.json`, GitHub Actions CI/CD workflows, and comprehensive documentation suite.

---

## [2.0.0] - 2026-09-26

### Added
- Multi-attempt non-linear problem solving modeling (`Episode` $\to$ `Attempt 1` $\to$ `Fail` $\to$ `Attempt 2` $\to$ `Success`).
- Epistemic node labeling (`:Fact`, `:Observation`, `:Inference`, `:Hypothesis`).
- Decision Support System (DSS) querying historical precedents and tradeoff rationales.
- Exploration Arc tracking (`Curiosity` $\to$ `Discovery` $\to$ `Prototype` $\to$ `Project`).
- Personal Cognitive Dashboard CLI (`cli.py`).
- Pre-ingestion regex secret redaction engine (`src/sanitizer.py`).

---

## [1.0.0] - 2026-09-23

### Added
- Initial Neo4j integration for basic episodic memory.
- Simple entity and relation storage.
- Append-only monthly JSONL event logging.
- Basic MCP stdio server.

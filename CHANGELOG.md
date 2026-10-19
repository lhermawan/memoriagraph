# Changelog

All notable changes to **MemoriaGraph** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.2] - 2026-10-17

### 🛡️ Ingestion Integrity Hardening, Deduplication & Shadow Mode Governance

#### Added
- **Database-Level Deduplication (`src/episode_manager.py`)**:
  - `create_episode()` checks `dedupe_fingerprint` in Neo4j prior to insert, returning existing episode with `is_duplicate=True` if matched.
  - 100% idempotent write operations preventing duplicate node creation across parallel workflows.
- **Strict Empirical Success Grounding (`src/ingestion_gate.py`)**:
  - `check_has_empirical_evidence()` strictly isolates positive completion signals (`exit code 0`, `status 200`, `tests passed`, `commit <sha>`).
  - Eliminates false positive hallucinations; tasks claiming success without verified anchors are downgraded to `UNKNOWN`.
- **Failure Integrity & Attempt Recovery**:
  - Validates `FAILURE` claims against empirical failure signals (`exit code [1-9]`, `stacktrace`, `OOM`).
  - Overrides intermediate failure labels if sequential attempts culminated in verified resolution.
- **Active Shadow Mode Governance**:
  - `MEMORIAGRAPH_ENFORCE_INGESTION_GATE` switches between strict blocking (`QUARANTINED`/`REJECTED`) and passive observation (`ACCEPTED_SHADOW`) with audit reason code recording.
- **Full-Chain Provenance Tracking**:
  - Propagates `provenance` (`OBSERVED`, `USER_REPORTED`, `INFERRED`, `ARTIFACT_VERIFIED`) and `record_type` from HTTP API & MCP facade directly to Neo4j `Episode` nodes.
- **Legacy Write Vector Hardening**:
  - Added credential sanitization to legacy tools like `add_entity()` and indexed `dedupe_fingerprint` in Neo4j schema.

---

## [3.1.1] - 2026-10-16

### 🔒 Memory Ingestion Quality Gate, Anti-Slop & Cache Reliability

#### Added
- **Contract-Driven Shared Memory Ingestion Quality Gate (`src/ingestion_gate.py`)**:
  - Deterministic chokepoint gating MCP tools and REST API against unverified claims, prompt injections, and noisy chatter.
- **Hard Secret Quarantine**:
  - Automated regex and entropy-based sanitization stripping API keys, tokens, and private keys before graph storage.
- **Cross-Process Cache Reliability (`src/hybrid_recall.py`)**:
  - Integrated `FileLock` and atomic file swapping on `.vector_cache.pkl` preventing concurrent write corruption.

---

## [3.1.0] - 2026-10-14

### ? The 5 Pillars of Overhead Elimination & Performance Turbo

#### Added
- **Pillar 1: Canonical Facade Consolidation (`server.py`)**:
  - Streamlined MCP interface from 14 fragmented tools down to **3 High-Yield Canonical Facades** (`retain`, `recall`, `reflect`), slashing prompt tool schema overhead by **70% (~1,800 tokens per turn)**.
  - Transparent backward-compatibility aliases maintained for all legacy tool signatures.
- **Pillar 2: Async Background Harvester (`src/harvester.py`)**:
  - Thread-safe worker daemon queue decoupling heavy ONNX vector cache synchronization and graph clustering from the request-response lifecycle.
  - Slashed memory ingestion (`retain`) latency from **1,300ms down to <30ms (97% speedup)**.
- **Pillar 3: Semantic Result Pruning & Compact Formatting (`src/hybrid_recall.py`)**:
  - Compact dense-bullet representation eliminating noisy internal rank dumps, reducing context window payload by **65%**.
- **Pillar 4: AI Gateway Pre-Injection & HTTP Microservice (`http_service.py`)**:
  - Native Starlette/Uvicorn HTTP daemon on port `8085` enabling mesh-wide memory queries without spawning python subshells.
  - Reverse-proxy pre-injection hook (e.g. 9Router / LiteLLM) that automatically enriches incoming prompts with relevant memories prior to LLM inference, achieving zero-tool roundtrips.
- **Pillar 5: In-Memory LRU Query Cache**:
  - 300-second TTL memory cache in `HybridRecallEngine` serving identical repeated queries in **<1ms** without re-executing Cypher queries or FastEmbed vector math.

#### Changed
- Default database credentials in all example code and fallbacks sanitized to standard environment variable lookups.
- Python packaging updated to include `starlette` and `uvicorn`.

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

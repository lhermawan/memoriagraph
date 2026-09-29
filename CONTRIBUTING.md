# Contributing to MemoriaGraph 3.0

Thank you for your interest in contributing to **MemoriaGraph**! MemoriaGraph is a biomimetic cognitive memory substrate built on the **Architectural Triad**:
- **Hindsight** (Episodic Substrate & Belief Revision)
- **Anti-Slop** (Immune System & Quality Gate)
- **Codebase-Memory** (Reality Anchor & Blast-Radius Mapping)

---

## 🛠️ Development Setup

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Docker & Neo4j 5.x+ (`memoriagraph-neo4j`)
- FastEmbed ONNX Runtime (CPU quantized Int8)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/maskii/memoriagraph.git
cd memoriagraph

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your Neo4j credentials
```

---

## 🧪 Testing Guidelines

Before submitting changes or PRs, all automated test suites must pass:

```bash
# Run all unit and integration tests
pytest tests/ -v

# Run the 4-Way Hybrid Recall benchmark
python test_hybrid_recall.py

# Run the Belief Revision hysteresis test
python test_belief_revision.py

# Run the Semantic Quality Gate anti-slop test
python test_semantic_sanitizer.py

# Run the Full Operational Benchmark suite
python benchmark_v3.py
```

---

## 📐 Architecture & Coding Rules

1. **Stdio Protocol Protection**:
   - `server.py` communicates with MCP hosts over standard I/O (JSON-RPC).
   - **NEVER** use plain `print(...)` in any library module, as it will corrupt the JSON-RPC communication stream! Always redirect debug output to `sys.stderr` or use `logger`.

2. **Pre-Ingestion Secret Redaction**:
   - Any new ingestion pipeline MUST route text through `src/sanitizer.py` and `src/semantic_sanitizer.py` before issuing Cypher write queries.

3. **Biomimetic Memory Bank Isolation**:
   - All newly recorded entities, episodes, and actions should explicitly specify their `memory_bank` (`infra-sre`, `ai-hud`, `research-personal`, `csirt-security`, `general`).

4. **Code Quality**:
   - Format code using `ruff format`.
   - Adhere to PEP 8 guidelines with maximum line length of 100 characters.
   - Include type annotations for all public functions.

---

## 🚀 Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-enhancement`
2. Commit with descriptive messages (e.g. `feat(recall): optimize int8 dense vector cache`).
3. Ensure all tests and benchmarks pass with zero regressions.
4. Open a Pull Request referencing related issues and describing changes thoroughly.

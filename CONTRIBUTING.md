# Contributing to MemoriaGraph 3.2

Thank you for your interest in contributing to **MemoriaGraph**! MemoriaGraph is a biomimetic cognitive memory substrate built on the **Architectural Triad**:
- **Hindsight** (Episodic Substrate & Belief Revision)
- **Anti-Slop** (Immune System & Quality Gate)
- **Codebase-Memory** (Reality Anchor & Blast-Radius Mapping)

---

## 🛠️ Development Setup

### 1. Prerequisites
- Python 3.10+ (Python 3.11 or 3.12 recommended)
- Docker & Neo4j 5.x+ (`memoriagraph-neo4j`)
- FastEmbed ONNX Runtime (CPU quantized Int8)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/lhermawan/memoriagraph.git
cd memoriagraph

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies in editable mode with development tools
pip install -e ".[dev]"

# Configure environment & dynamic credentials interactively
python installer.py
# Or copy template manually:
# cp .env.example .env
```

---

## 🧪 Testing Guidelines

Before submitting changes or PRs, all automated test suites must pass:

```bash
# Run the complete unified test suite
python tests/run_all.py

# Or run pytest directly
pytest tests/ -v

# Run the full operational benchmark suite
python benchmark_v3.py
```

---

## 📐 Architecture & Coding Rules

1. **Stdio Protocol Protection**:
   - `server.py` communicates with MCP hosts over standard I/O (JSON-RPC).
   - **NEVER** use plain `print(...)` in any library module, as it will corrupt the JSON-RPC communication stream! Always redirect debug output to `sys.stderr` or use `logger`.

2. **Pre-Ingestion Secret Redaction**:
   - Any new ingestion pipeline MUST route text through `src/sanitizer.py` and `src/semantic_sanitizer.py` before issuing Cypher write queries.

3. **Dynamic Memory Bank Registry**:
   - All newly recorded entities, episodes, and actions should specify their `bank_id` using the dynamic memory bank registry (`banks.json`).
   - Default universal categories: `general`, `codebase`, `operations`, `research`.
   - Users and agents can dynamically define custom memory banks via `python cli.py banks add <id>`.

4. **Zero Hardcoded Credentials**:
   - Never commit or hardcode database passwords. Always retrieve credentials through `src.config` (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).

5. **Code Quality**:
   - Format code using `ruff format`.
   - Adhere to PEP 8 guidelines with maximum line length of 100 characters.
   - Include type annotations for all public functions.

---

## 🚀 Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-enhancement`
2. Commit with descriptive conventional commit messages (e.g. `feat(recall): optimize int8 dense vector cache`).
3. Ensure all tests and benchmarks pass with zero regressions (`python tests/run_all.py`).
4. Open a Pull Request referencing related issues and describing changes thoroughly.

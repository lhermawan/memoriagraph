# 🏛️ MemoriaGraph Architecture: Cognitive Substrate & Retrieval Engine

**MemoriaGraph 3.2** unifies three core engineering pillars into a resilient, sovereign, biomimetic cognitive memory substrate for autonomous AI agents, enterprise pipelines, and multi-agent swarms:

```
                  ┌──────────────────────────────────────────────┐
                  │              MemoriaGraph 3.2                │
                  │   Cognitive Substrate & Retrieval Engine     │
                  └──────────────────────┬───────────────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
  ┌──────────────┐                ┌──────────────┐                ┌──────────────┐
  │  HINDSIGHT   │                │  ANTI-SLOP   │                │   CODEBASE   │
  │    MEMORY    │                │    IMMUNE    │                │    MEMORY    │
  │  SUBSTRATE   │                │    SYSTEM    │                │REALITY ANCHOR│
  └──────────────┘                └──────────────┘                └──────────────┘
         │                               │                               │
         └───────────────────────┬───────┴───────────────────────────────┘
                                 ▼
       ┌───────────────────────────────────────────────────┐
       │             CANONICAL HINDSIGHT FACADES           │
       │    client.retain()  │  recall()  │  reflect()     │
       └─────────────────────────┬─────────────────────────┘
                                 │
     ┌───────────────────────────┴───────────────────────────┐
     ▼                                                       ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│  4-WAY HYBRID RECALL (RRF)    │               │  ASYNC BACKGROUND HARVESTER   │
│ • BM25 Fulltext Index         │               │ • Non-blocking queue write    │
│ • 2-Hop Graph Traversal       │               │ • Int8 FastEmbed ONNX local   │
│ • Temporal Exponential Decay  │               │ • Write latency: <30ms        │
│ • Dense Int8 Vector Embedding │               │ • In-Memory LRU Cache (300s)  │
└──────────────┬────────────────┘               └───────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│             INTEGRATION & SERVING LAYER                │
│ • Universal MCP (Antigravity, Claude, Cursor, Copilot) │
│ • High-Performance HTTP Microservice (Port 8085)       │
│ • OpenAPI 3.1.0 for ChatGPT Custom GPT Actions         │
│ • Cybernetic Cockpit 3D Visualizer & Taskbar Tray      │
└────────────────────────────────────────────────────────┘
```

---

## 1. 🧠 Pilar 1: Hindsight (Memory Substrate)
*Inspired by the cognitive consolidation mechanisms of human memory and research into dual-process reflection.*

### Core Functions:
1. **Episodic & Semantic Dual-Store**:
   - **Episodes**: Capture temporal, multi-attempt problem-solving trajectories (`Attempt 1 -> Fail -> Attempt 2 -> Success`), recording decisions, constraints, and root causes.
   - **Semantics**: Extract timeless concepts, interconnected domain entities, and operational constraints in the Neo4j property graph.
2. **Dynamic Universal Memory Banks**:
   Memory banks provide strict context isolation so information from one domain never pollutes another, dynamically managed via `banks.json` and CLI (`python cli.py banks`):
   - `general`: Cross-domain common sense, general dialogue, and heuristics.
   - `codebase`: Code architecture, bug fixes, refactoring, and AST blast radius.
   - `operations`: DevOps, Docker, server topologies, system monitoring, and incidents.
   - `research`: Emerging tech exploration, papers, benchmark evaluations, and prototypes.
   - *Custom Banks*: Freely defined by users and teams for dedicated projects without hardcoded partition limits.
3. **Consolidation & Crystallization**:
   - Candidate observations (`CANDIDATE`) graduate to confirmed heuristics (`OBSERVED`) and eventually crystallize into permanent cognitive patterns (`HIGH_CONFIDENCE`).

---

## 2. 🛡️ Pilar 2: Anti-Slop (Immune System)
*Providing an active filter against LLM fluff, hallucinatory claims, and leaked credentials.*

### Core Functions:
1. **Deterministic Redaction**:
   - Strips private keys (`BEGIN RSA...`), API keys (`sk_live_...`, tokens), passwords, and sensitive connection strings prior to database write.
2. **Boilerplate & Fluff Stripper**:
   - Purges conversational pleasantries (*"Certainly!", "I hope this helps!", "As an AI..."*) and redundant concluding summaries.
3. **Epistemic Grounding Gate**:
   - Prevents unverified performance claims (e.g. *"reduced memory by 90%"*) unless grounded by actual numeric telemetry or process exit codes.
4. **Code Comment Cleaner**:
   - Strips trivial and obvious comments (e.g. `// increment counter`) before storing code snippets in Neo4j.

---

## 3. ⚓ Pilar 3: Codebase-Memory (Reality Anchor)
*Grounding memory in the concrete, verifiable state of repository files and version control.*

### Core Functions:
1. **Git Blast-Radius Mapping**:
   - Automatically computes git diffs, modified functions, affected directories, and blast severity when an action is executed.
2. **AST Node Linking**:
   - Connects `:Action` nodes to the concrete files and repositories they modified.
3. **Ghost-Edit Prevention**:
   - By querying historical code actions, the agent avoids re-introducing previously rejected changes or breaking architectural invariants.

---

## 4. ⚡ High-Performance Retrieval & Serving (Version 3.2)

### 3 Canonical Facades
Consolidates granular operations down to 3 unified, intuitive facades:
- `retain()`: Ingests structured episodes, SOPs, and facts into dynamic memory banks with automatic asynchronous background vectorization.
- `recall()`: Executes 4-Way Hybrid Recall with Reciprocal Rank Fusion (RRF), compact result pruning, and sub-millisecond in-memory caching.
- `reflect()`: Synthesizes past problem-solving trajectories and executes mathematical belief calibration (`action="reinforce"` or `action="challenge"`).

### Serving & Integration Modes
- **Universal MCP Stdio**: Native standard input/output interface with 1-click configuration for Google Antigravity, Anthropic Claude Desktop, Cursor IDE, VS Code / Copilot, and Windsurf.
- **HTTP Microservice & OpenAPI 3.1 (Port 8085)**: RESTful API for multi-agent swarms, n8n automations, and native ChatGPT Custom GPT Actions (`/openapi.json`, `/health`, `/recall`, `/retain`).
- **Cybernetic Cockpit & Taskbar Companion**: Live 3D force-directed graph visualization and silent background system tray monitor for desktop environments.

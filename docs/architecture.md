# 🏛️ MemoriaGraph Architecture: Cognitive Substrate & Retrieval Engine

**MemoriaGraph 3.1** unifies three core engineering pillars into a resilient, biomimetic cognitive memory substrate for autonomous AI agents, enterprise pipelines, and multi-agent swarms:

```
                  ┌──────────────────────────────────────────────┐
                  │              MemoriaGraph 3.1                │
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
│ • Standard Model Context Protocol (MCP stdio)          │
│ • High-Performance HTTP Microservice (Port 8085)       │
│ • Zero-Roundtrip AI Gateway Pre-Injection (9Router)    │
└────────────────────────────────────────────────────────┘
```

---

## 1. 🧠 Pilar 1: Hindsight (Memory Substrate)
*Inspired by the cognitive consolidation mechanisms of human memory and research into dual-process reflection.*

### Core Functions:
1. **Episodic & Semantic Dual-Store**:
   - **Episodes**: Capture temporal, multi-attempt problem-solving trajectories (`Attempt 1 -> Fail -> Attempt 2 -> Success`), recording decisions, constraints, and root causes.
   - **Semantics**: Extract timeless concepts, interconnected domain entities, and operational constraints in the Neo4j property graph.
2. **Biomimetic Memory Banks**:
   Memory banks provide strict context isolation so information from one domain never pollutes another:
   - `production-infra`: Server topologies, process managers, TLS certificates, watchdog incidents.
   - `core-dev`: Architecture decisions, AST modifications, code actions, blast radiuses.
   - `security-audit`: CVE reports, penetration testing observations, firewall configurations.
   - `research-experiments`: Model evaluations, benchmark results, cognitive tracking.
   - `general`: Cross-domain common sense and system heuristics.
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

## 4. ⚡ High-Performance Retrieval & Serving (Version 3.1)

### 3 Canonical Facades
Consolidates 14 granular tools down to 3 unified, intuitive facades:
- `retain()`: Ingests structured episodes, SOPs, and facts into isolated memory banks with automatic asynchronous background vectorization.
- `recall()`: Executes 4-Way Hybrid Recall with Reciprocal Rank Fusion (RRF), compact result pruning, and sub-millisecond in-memory caching.
- `reflect()`: Synthesizes past problem-solving trajectories and executes mathematical belief calibration (`action="reinforce"` or `action="challenge"`).

### Serving & Integration Modes
- **MCP Stdio**: Native standard input/output interface for Claude Desktop, Cursor, Gemini CLI, and Windsurf.
- **HTTP Microservice (Port 8085)**: RESTful API for multi-agent swarms, n8n automations, and web backends (`/health`, `/recall`, `/retain`, `/reflect`).
- **AI Gateway Pre-Injection**: Zero-tool roundtrip interception via `x-memoriagraph-inject` header in AI proxies (9Router, LiteLLM), inserting relevant context directly into the system prompt.

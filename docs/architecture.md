# 🏛️ MemoriaGraph Architecture: The Triad

MemoriaGraph 3.0 unifies three core engineering pillars to create a resilient, biomimetic memory substrate for autonomous AI agents:

```
                  ┌──────────────────────────────┐
                  │      MemoriaGraph 3.0        │
                  │   The Architectural Triad    │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
  │  HINDSIGHT   │        │  ANTI-SLOP   │        │   CODEBASE   │
  │    MEMORY    │        │    IMMUNE    │        │    MEMORY    │
  │  SUBSTRATE   │        │    SYSTEM    │        │REALITY ANCHOR│
  └──────────────┘        └──────────────┘        └──────────────┘
```

---

## 1. 🧠 Pilar 1: Hindsight (Memory Substrate)
*Inspired by the cognitive consolidation mechanisms of human memory and research into dual-process reflection.*

### Core Functions:
1. **Episodic & Semantic Dual-Store**:
   - Episodes capture temporal, multi-attempt problem-solving trajectories (`Attempt 1 -> Fail -> Attempt 2 -> Success`).
   - Semantics extract timeless concepts, entities, and constraints.
2. **Biomimetic Memory Banks**:
   - `infra-sre`: Production server nodes, PM2 processes, SSL certificates, Watchdog alerts.
   - `ai-hud`: Three.js WebGL telemetry, Arc Reactor state, 144Hz HUD parameters.
   - `research-personal`: Experiments, new AI papers, tool benchmarks, evaluations.
   - `csirt-security`: Vulnerabilities, pentest reports, firewall rules, Kali sandbox results.
   - `general`: Cross-domain common sense and system heuristics.
3. **Consolidation & Crystallization**:
   - Candidate observations (`CANDIDATE`) graduate to confirmed heuristics (`OBSERVED`) and eventually crystallize into permanent cognitive patterns (`HIGH_CONFIDENCE`).

---

## 2. 🛡️ Pilar 2: Anti-Slop (Immune System)
*Inspired by `miqdadbadjuber/anti-slop`, providing an active filter against LLM fluff and hallucinations.*

### Core Functions:
1. **Deterministic Redaction**:
   - Strips private keys, API tokens, and connection strings prior to database write.
2. **Boilerplate & Fluff Stripper**:
   - Purges empty conversational pleasantries (*"Certainly!", "I hope this helps!", "As an AI..."*) and redundant concluding summaries.
3. **Epistemic Grounding Gate**:
   - Prevents unverified performance claims (e.g. *"reduced memory by 90%"*) unless grounded by actual numeric telemetry or process exit codes.
4. **Code Comment Cleaner**:
   - Strips trivial and obvious comments (e.g. `// increment counter`) before storing code snippets in Neo4j.

---

## 3. ⚓ Pilar 3: Codebase-Memory (Reality Anchor)
*Inspired by `DeusData/codebase-memory-mcp`, grounding memory in the actual state of files and repositories.*

### Core Functions:
1. **Git Blast-Radius Mapping**:
   - Automatically computes git diffs, modified functions, and file paths when an action is executed.
2. **AST Node Linking**:
   - Connects `:Action` nodes to the concrete files and repositories they modified.
3. **Ghost-Edit Prevention**:
   - By querying historical code actions, the agent avoids re-introducing previously rejected changes or breaking architectural invariants.

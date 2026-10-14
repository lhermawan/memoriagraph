# 📘 Institutional & Organizational Training Guide for MemoriaGraph
> **Building a Sovereign "Second Brain" for Public Agencies & Enterprises using Cognitive Knowledge Graphs**  
> *Version: 3.1.0 | Open-Source Enterprise & Gov-Tech*

*(Untuk versi bahasa Indonesia lengkap, silakan baca [PANDUAN_PELATIHAN_INSTANSI.md](PANDUAN_PELATIHAN_INSTANSI.md))*

---

## 🏛️ 1. Why Institutions Need MemoriaGraph

Traditional LLM fine-tuning is cost-prohibitive, leaks sensitive organizational data to external cloud providers, and suffers from hallucinations and stale knowledge. In contrast, **MemoriaGraph 3.1** provides a dual-store episodic-semantic substrate anchored by:
* **Zero Data Leakage:** On-premise Neo4j deployment protected by the Anti-Slop Immune Gate.
* **Knowledge Retention upon Personnel Rotation:** Troubleshooting heuristics, operational decisions, and incident post-mortems are preserved permanently.
* **Continuous Experiential Learning:** Knowledge evolves dynamically through real operational episodes and empirical feedback loops.
* **Zero-Tool Overhead:** Supports both direct Model Context Protocol (MCP) and zero-roundtrip AI Gateway Pre-Injection via HTTP microservice.

---

## 🚀 2. Standard Workflow: Training the Institutional Brain

### Step 1: Memory Bank Partitioning
Divide operational domains to avoid cross-domain context contamination:
* `enterprise-services`: Citizen portals, e-Gov API gateways, microservices.
* `security-csirt`: Incident response logs, vulnerability audits, firewall rules.
* `infra-server`: Cloud/on-prem topology, VM health metrics, reboot SOPs.
* `compliance-policy`: Regulatory mandates, legal decrees, internal procedures.

### Step 2: Baseline Knowledge Ingestion (`retain`)
Store official SOPs, guidelines, and manuals using the unified `retain` facade tool:
```python
retain(
    bank_id="infra-server",
    category="SOP",
    title="Service Recovery SOP for Gateway Daemon",
    content="Verify systemd unit: systemctl status api-daemon. Restart via systemctl restart api-daemon. Verify port 8080 is listening on 127.0.0.1.",
    heuristic="Always check systemd unit states before attempting a full VM reboot."
)
```

### Step 3: Experiential Episode Recording (`retain`)
Every resolved incident, post-mortem, or major architectural change should be recorded with its problem statement, attempts, decisions, outcomes, and golden heuristics:
```python
retain(
    bank_id="infra-server",
    category="Incident",
    title="Post-Mortem: Database Connection Pool Starvation",
    content="Resolved 504 Gateway Timeouts by tuning max_connections from 100 to 500 and enabling pgBouncer session pooling.",
    decision="Adopted pgBouncer connection pooling to prevent backend thread exhaustion.",
    heuristic="Always decouple high-concurrency HTTP workers from direct relational database connection limits."
)
```

### Step 4: Dynamic Belief Revision & Reflection (`reflect`)
* **Reinforce:** Confirmed heuristics gain logarithmic confidence boost. After $\ge 3$ validations, they crystallize into permanent `Pattern` nodes (`HIGH_CONFIDENCE`).
* **Challenge:** Obsolete or failing procedures undergo hysteresis dampening and transition to `CONTESTED` or `DEPRECATED`.
```python
# Reinforce a proven rule:
reflect(
    target_id="heuristic-pgbouncer-pooling",
    action="reinforce",
    reason="Validated successfully during peak traffic hours with 0 dropped connections"
)
```

### Step 5: Fast Retrieval & Decision Support (`recall`)
Staff members, autonomous agents, and leadership can query the institutional memory:
* `recall(query="database timeout", bank_id="infra-server")` for relevant SOPs, prior incidents, and golden heuristics.
* Or query via HTTP microservice: `curl "http://127.0.0.1:8085/recall?query=database+timeout&compact=true"`

---

For full operational templates, Cypher queries, and compliance guidelines, refer to [`docs/PANDUAN_PELATIHAN_INSTANSI.md`](PANDUAN_PELATIHAN_INSTANSI.md).

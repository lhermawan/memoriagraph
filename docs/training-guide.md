# 📘 Institutional & Organizational Training Guide for MemoriaGraph
> **Building a Sovereign "Second Brain" for Public Agencies & Enterprises using Cognitive Knowledge Graphs**  
> *Version: 3.0.0 | Open-Source Enterprise & Gov-Tech*

*(Untuk versi bahasa Indonesia lengkap, silakan baca [PANDUAN_PELATIHAN_INSTANSI.md](PANDUAN_PELATIHAN_INSTANSI.md))*

---

## 🏛️ 1. Why Institutions Need MemoriaGraph

Traditional LLM fine-tuning is cost-prohibitive, leaks data to external cloud providers, and suffers from hallucinations and stale knowledge. In contrast, **MemoriaGraph 3.0** provides a dual-store episodic-semantic substrate anchored by:
* **Zero Data Leakage:** On-premise Neo4j deployment protected by the Anti-Slop Immune Gate.
* **Knowledge Retention upon Personnel Rotation:** Troubleshooting heuristics and architectural decisions are preserved forever.
* **Continuous Experiential Learning:** Knowledge evolves through real operational episodes and feedback loops.

---

## 🚀 2. Quick Workflow: Training the Graph Brain

### Step 1: Memory Bank Partitioning
Divide operational domains to avoid cross-domain contamination:
* `spbe-layanan`: Citizen services, e-Gov API gateways, app registries.
* `csirt-security`: Incident logs, vulnerability reports, firewall rules.
* `infra-server`: Hardware topology, VM metrics, reboot SOPs.
* `regulasi-kebijakan`: Regulations, local government decrees, SOPs.

### Step 2: Baseline Knowledge Ingestion (`retain`)
Store official SOPs, guidelines, and manuals using the `retain` facade tool:
```python
retain(
    bank_id="infra-server",
    category="SOP",
    title="Service Recovery SOP for SPBE API Daemon",
    content="Check systemd unit: systemctl status ai-sre-daemon. Restart via systemctl restart ai-sre-daemon. Verify port 3400 is listening on 127.0.0.1.",
    heuristic="Always check systemd unit states before attempting a full VM reboot."
)
```

### Step 3: Experiential Episode Recording (`record_cognitive_episode`)
Every resolved incident, post-mortem, or major architectural change should be recorded with its problem statement, attempts, decisions, outcomes, and golden heuristics.

### Step 4: Dynamic Belief Revision (`reinforce_belief` & `challenge_belief`)
* **Reinforce:** Confirmed heuristics gain logarithmic confidence boost. After $\ge 3$ validations, they crystallize into permanent `Pattern` nodes (`HIGH_CONFIDENCE`).
* **Challenge:** Obsolete or failing procedures undergo hysteresis dampening and transition to `CONTESTED` or `DEPRECATED`.

### Step 5: Decision Support Querying (`query_dss` & `recall`)
Staff members and leadership can consult the institutional memory:
* `recall(query, bank_id)` for relevant SOPs and technical documentation.
* `query_dss(situation, context)` for evidence-based decision support, historical success rates, and proven heuristics.

---

For full details, forms, and compliance with data privacy regulations, refer to [`docs/PANDUAN_PELATIHAN_INSTANSI.md`](PANDUAN_PELATIHAN_INSTANSI.md).

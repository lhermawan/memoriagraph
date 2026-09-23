# 🧠 MemoriaGraph

> **Persistent memory for AI assistants — powered by Knowledge Graph**

MemoriaGraph gives your AI a permanent, structured memory that persists across sessions, projects, and conversations. No more re-explaining your architecture every time.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://hub.docker.com)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

---

## ✨ Features

- 🔗 **Knowledge Graph** — entities and relations, not just flat key-value memory
- 🖥️ **Visual Explorer** — see your AI's memory as an interactive graph via Neo4j Browser
- 🔒 **Self-Hosted** — your data never leaves your server
- 🤖 **MCP Compatible** — plug into Claude, Gemini, Antigravity, and any MCP-compatible AI
- ⚡ **Fast Context Retrieval** — AI instantly knows your project on every new session

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/lhermawan/memoriagraph.git
cd memoriagraph

# 2. Start with Docker
docker compose up -d

# 3. Done! MemoriaGraph is running at:
#    MCP Server  → http://localhost:3000
#    Neo4j Browser → http://localhost:7474
```

---

## 🧩 How It Works

```
Your AI Assistant
      │
      ▼
 MCP Protocol
      │
      ▼
MemoriaGraph Server  ──→  Neo4j Database
      │                        │
      │                        ▼
      │               Knowledge Graph
      │               (Entities + Relations)
      ▼
Context returned to AI → "I already know your project!"
```

---

## 📡 MCP Tools

| Tool | Description |
|---|---|
| `add_entity` | Save a named entity (server, project, person, etc.) |
| `add_relation` | Connect two entities with a relationship |
| `get_context` | Retrieve relevant context for the current session |

### Example Usage

```python
# Save a server
add_entity(name="Production Server", entity_type="Server", description="IP: 192.168.1.1, Port: 22")

# Connect it to a project
add_relation(source_name="Production Server", relationship="HOSTS", target_name="My App")

# Next session — AI retrieves context automatically
get_context(query="production server")
# → Returns: Production Server, IP, what it hosts, related entities
```

---

## 🗺️ Visual Memory Explorer

Open `http://localhost:7474` in your browser and run:

```cypher
MATCH (n)-[r]->(m) RETURN n, r, m
```

You'll see your entire project memory as an interactive node graph! 🕸️

---

## ⚙️ Configuration

```env
# .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
MCP_PORT=3000
```

---

## 🗂️ Project Structure

```
memoriagraph/
├── docker-compose.yml     # One-command setup
├── mcp/
│   └── server.py          # MCP server (add_entity, add_relation, get_context)
├── .env.example           # Environment variables template
├── README.md
└── CONTRIBUTING.md
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

> *"A great AI isn't just smart — it remembers."*
> — MemoriaGraph

#!/usr/bin/env bash
# ==============================================================================
# MemoriaGraph 3.2 - One-Line Docker Deployment Script
# Usage: curl -fsSL https://raw.githubusercontent.com/lhermawan/memoriagraph/main/scripts/docker-run.sh | bash
# ==============================================================================
set -e

echo "🧠 [MemoriaGraph] Initializing One-Line Autonomous Setup..."

if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker and Docker Compose first."
    exit 1
fi

INSTALL_DIR="${HOME}/.memoriagraph"
if [ -d "$INSTALL_DIR" ]; then
    echo "📁 Existing installation found at $INSTALL_DIR. Updating repository..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "📦 Cloning MemoriaGraph to $INSTALL_DIR..."
    git clone https://github.com/lhermawan/memoriagraph.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "🚀 Starting MemoriaGraph Containers (Neo4j Community + MemoriaGraph Engine)..."
docker compose up -d --build

echo ""
echo "=============================================================================="
echo "🎉 MemoriaGraph 3.2 is up and running!"
echo "=============================================================================="
echo "🌐 Cybernetic Cockpit & API : http://localhost:8085"
echo "🗄️ Neo4j Database Browser   : http://localhost:7474 (user: neo4j, pass: memoriagraph_pass)"
echo "⚡ MCP Server endpoint       : Integrated stdio / HTTP microservice"
echo ""
echo "To check container logs:"
echo "  docker compose logs -f memoriagraph"
echo "=============================================================================="

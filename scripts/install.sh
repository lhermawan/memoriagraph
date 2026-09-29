#!/usr/bin/env bash
set -e

echo "🚀 Installing MemoriaGraph 3.0..."

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies in editable mode..."
venv/bin/pip install --upgrade pip
venv/bin/pip install -e ".[dev]"

if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env from template..."
    cp .env.example .env
fi

echo "🧠 Initializing Neo4j Schema & Fulltext Indexes..."
venv/bin/python -c "from src.schema_init import init_schema; init_schema()"

echo "✅ MemoriaGraph 3.0 installation completed successfully!"
echo "👉 Run 'venv/bin/memoria dashboard' or 'venv/bin/python benchmark_v3.py' to verify."

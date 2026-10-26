#!/usr/bin/env bash
set -e

# MemoriaGraph 3.2.0 - Linux & macOS Installer
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

export PYTHONIOENCODING="utf-8"

echo "============================================================"
echo "🧠 MemoriaGraph 3.2.0 - Universal Unix Installer"
echo "============================================================"

# Cek Python 3
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "❌ Python 3 tidak ditemukan. Silakan pasang Python 3.10+ terlebih dahulu."
    exit 1
fi

# Jalankan installer Python modular
"$PYTHON_BIN" installer.py "$@"

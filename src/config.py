"""
MemoriaGraph 3.2 - Centralized Portable Configuration
Decouples repository and runtime paths from static infrastructure (/opt/memoriagraph)
Supports Linux, macOS, Windows, and Docker environments seamlessly.
"""
import os
import sys
from pathlib import Path
import dotenv

# Dynamically resolve repository root (directory containing server.py, src/, etc.)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Ensure ROOT_DIR is in sys.path for clean submodule imports
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Base working directory (defaults to repo root, can be overridden via MEMORIAGRAPH_HOME)
MEMORIAGRAPH_HOME = Path(os.getenv("MEMORIAGRAPH_HOME", str(ROOT_DIR)))

# Load .env: first check MEMORIAGRAPH_HOME/.env, then ROOT_DIR/.env, then fallback to dotenv search
env_home = MEMORIAGRAPH_HOME / ".env"
env_root = ROOT_DIR / ".env"
if env_home.exists():
    dotenv.load_dotenv(env_home)
elif env_root.exists():
    dotenv.load_dotenv(env_root)
else:
    dotenv.load_dotenv()

# Database credentials
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_secure_password")

# Storage & Cache Directories
VECTOR_CACHE_FILE = os.getenv("VECTOR_CACHE_FILE", str(MEMORIAGRAPH_HOME / ".vector_cache.pkl"))
EVENTS_DIR = os.getenv("EVENTS_DIR", str(MEMORIAGRAPH_HOME / "events"))
LOGS_DIR = os.getenv("LOGS_DIR", str(MEMORIAGRAPH_HOME / "logs"))
BACKUPS_DIR = os.getenv("BACKUPS_DIR", str(MEMORIAGRAPH_HOME / "backups"))

# Security Gateway Configuration
# Options: 'private' (default - allows loopback, Tailscale, & RFC1918 private subnets/Docker),
#          'tailscale' (strict - allows loopback & Tailscale 100.64.0.0/10 only),
#          'all' (open - for setups behind trusted reverse proxies)
SECURITY_NETWORK_MODE = os.getenv("SECURITY_NETWORK_MODE", "private").lower()

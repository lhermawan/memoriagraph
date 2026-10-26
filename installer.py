#!/usr/bin/env python3
"""
MemoriaGraph 3.2.0 - Universal Modular Installer & Setup Wizard
Provides 1-Click setup for Local Mode (Claude Desktop + Docker Neo4j + Tray)
and Server Mode (Docker Compose Microservice + Cockpit).
"""
import argparse
import json
import os
import platform
import secrets
import shutil
import socket
import string
import subprocess
import sys
import time
from pathlib import Path

# Base project directory
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Defensive Windows console UTF-8 reconfiguration
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from src.bank_manager import bank_manager

VERSION = "3.2.0"

def init_terminal_colors():
    """
    Mengaktifkan Windows Virtual Terminal Processing untuk ANSI colors.
    Jika terminal tidak mendukung ANSI escape sequence, warna dinonaktifkan
    secara elegan agar tidak mencetak karakter mentah seperti '[1;36m'.
    """
    c_cyan = "\033[1;36m"
    c_green = "\033[1;32m"
    c_yellow = "\033[1;33m"
    c_red = "\033[1;31m"
    c_reset = "\033[0m"
    c_bold = "\033[1m"

    if os.environ.get("NO_COLOR"):
        return "", "", "", "", "", ""

    if hasattr(sys.stdout, "isatty") and not sys.stdout.isatty():
        return "", "", "", "", "", ""

    if sys.platform == "win32":
        vt_ok = False
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            hStdOut = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode)):
                if kernel32.SetConsoleMode(hStdOut, mode.value | 0x0004):
                    vt_ok = True
        except Exception:
            pass

        try:
            os.system("")
            vt_ok = True
        except Exception:
            pass

        if any(k in os.environ for k in ("WT_SESSION", "TERM_PROGRAM", "ANSICON", "ConEmuANSI")):
            vt_ok = True

        if not vt_ok:
            return "", "", "", "", "", ""

    return c_cyan, c_green, c_yellow, c_red, c_reset, c_bold

CYAN, GREEN, YELLOW, RED, RESET, BOLD = init_terminal_colors()


# Terminal emoji support detection
SUPPORTS_EMOJI = bool(
    os.environ.get("WT_SESSION") or 
    os.environ.get("TERM_PROGRAM") in ("vscode", "hyper", "iTerm.app", "WezTerm", "Alacritty") or
    (sys.platform != "win32" and "UTF-8" in os.environ.get("LANG", "").upper())
)
USE_EMOJI = SUPPORTS_EMOJI and not os.environ.get("PLAIN_TEXT")

SYM_BRAIN = "🧠" if USE_EMOJI else "[MG]"
SYM_LOCAL = "💻" if USE_EMOJI else "[LOCAL]"
SYM_SERVER = "🌐" if USE_EMOJI else "[SERVER]"
SYM_TRAY = "🖥️" if USE_EMOJI else "[TRAY]"
SYM_BANKS = "🏦" if USE_EMOJI else "[BANKS]"
SYM_AI = "🤖" if USE_EMOJI else "[AI]"
SYM_OK = "✅" if USE_EMOJI else "[OK]"
SYM_FAIL = "❌" if USE_EMOJI else "[FAIL]"
SYM_WARN = "⚠️" if USE_EMOJI else "[!]"
SYM_SEARCH = "🔍" if USE_EMOJI else "[*]"
SYM_DOCKER = "🐳" if USE_EMOJI else "[DOCKER]"
SYM_SUCCESS = "🎉" if USE_EMOJI else "[SUCCESS]"
SYM_PKG = "📦" if USE_EMOJI else "[PKG]"
SYM_INFO = "ℹ️" if USE_EMOJI else "[INFO]"
BORDER = "═" * 65 if USE_EMOJI else "=" * 65
BORDER_SUB = "═" * 50 if USE_EMOJI else "=" * 50


def safe_input(prompt: str = "") -> str:
    """Membaca input terminal dengan aman dari UTF-8 BOM PowerShell dan EOF."""
    try:
        raw = input(prompt)
        return raw.strip().lstrip("\ufeff")
    except (EOFError, KeyboardInterrupt):
        return ""


def print_banner():
    print(f"\n{CYAN}{BORDER}")
    print(f"{SYM_BRAIN} MEMORIAGRAPH v{VERSION} - UNIVERSAL MODULAR INSTALLER")
    print(f"{BORDER}{RESET}\n")


def check_python_version() -> bool:
    """Memastikan Python host memenuhi syarat minimal >= 3.10."""
    v = sys.version_info
    print(f"{SYM_SEARCH} Memeriksa versi Python host: {v.major}.{v.minor}.{v.micro}...", end=" ")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"{RED}GAGAL!{RESET}")
        print(f"{SYM_FAIL} MemoriaGraph membutuhkan Python 3.10 atau lebih baru.")
        return False
    print(f"{GREEN}{SYM_OK}{RESET}")
    return True


def get_venv_python() -> Path:
    """Mengembalikan path executable Python virtual environment lokal."""
    is_win = sys.platform == "win32"
    candidates = [
        ROOT_DIR / ".venv" / ("Scripts/python.exe" if is_win else "bin/python"),
        ROOT_DIR / "venv" / ("Scripts/python.exe" if is_win else "bin/python"),
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback to current running interpreter
    return Path(sys.executable)


def ensure_virtualenv(dry_run: bool = False) -> Path:
    """Memastikan virtual environment .venv ada dan dependensi terpasang."""
    venv_dir = ROOT_DIR / ".venv"
    venv_python = get_venv_python()

    if not venv_dir.exists() and not (ROOT_DIR / "venv").exists():
        print(f"{SYM_PKG} Membuat virtual environment baru di {venv_dir}...")
        if not dry_run:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
            venv_python = get_venv_python()
            print(f"{SYM_OK} Virtual environment berhasil dibuat.")

    print(f"{SYM_PKG} Memastikan dependensi utama terinstal...")
    if not dry_run:
        pip_cmd = [str(venv_python), "-m", "pip", "install", "-e", "."]
        try:
            subprocess.run(pip_cmd, cwd=str(ROOT_DIR), check=True)
            print(f"{GREEN}{SYM_OK} Dependensi MemoriaGraph terverifikasi lengkap!{RESET}")
        except Exception as e:
            print(f"{YELLOW}{SYM_WARN} Catatan instalasi pip: {e}{RESET}")

    return venv_python


def test_neo4j_socket(host: str = "127.0.0.1", port: int = 7687, timeout: float = 2.0) -> bool:
    """Tes cepat apakah port Bolt Neo4j aktif dan menerima koneksi."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def test_neo4j_auth(uri: str, user: str, passw: str) -> bool:
    """Tes otentikasi driver Neo4j."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, passw))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


def is_docker_available() -> bool:
    """Mengecek apakah Docker terpasang dan daemon berjalan."""
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def generate_secure_password(length: int = 16) -> str:
    """Menghasilkan password acak berkeamanan tinggi yang ramah shell."""
    chars = string.ascii_letters + string.digits + "_-@#"
    return "".join(secrets.choice(chars) for _ in range(length))


def prompt_neo4j_credentials(default_user: str = "neo4j", default_pass: str = None) -> tuple[str, str]:
    """
    Meminta username & password Neo4j secara interaktif.
    Menghilangkan default hardcoded password. Jika user menekan Enter,
    otomatis dibuatkan password acak aman 16-karakter.
    """
    print(f"\n{CYAN}{BORDER_SUB}")
    print("🔒 KONFIGURASI KREDENSIAL DATABASE NEO4J")
    print(f"{BORDER_SUB}{RESET}")
    print("Atur username dan password database untuk keamanan maksimal:\n")

    user_inp = safe_input(f"Username Neo4j [default: {default_user}]: ").strip()
    user = user_inp if user_inp else default_user

    generated_pw = default_pass or generate_secure_password()
    print(f"💡 Tips: Tekan Enter untuk menggunakan password acak aman:")
    print(f"   Password yang disarankan: {BOLD}{GREEN}{generated_pw}{RESET}")

    prompt_label = f"Password Neo4j [Enter untuk '{generated_pw}']: "
    pass_inp = safe_input(prompt_label).strip()
    passw = pass_inp if pass_inp else generated_pw

    print(f"\n{GREEN}{SYM_OK} Kredensial aktif: User '{BOLD}{user}{RESET}', Password tersimpan aman.{RESET}")
    return user, passw


def save_env_credentials(uri: str, user: str, passw: str, env_path: Path = None):
    """Menyimpan atau memperbarui NEO4J_URI, NEO4J_USER, dan NEO4J_PASSWORD di file .env."""
    if env_path is None:
        env_path = ROOT_DIR / ".env"

    env_lines = []
    keys_found = {"NEO4J_URI": False, "NEO4J_USER": False, "NEO4J_PASSWORD": False}

    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("NEO4J_URI="):
                        env_lines.append(f"NEO4J_URI={uri}\n")
                        keys_found["NEO4J_URI"] = True
                    elif stripped.startswith("NEO4J_USER="):
                        env_lines.append(f"NEO4J_USER={user}\n")
                        keys_found["NEO4J_USER"] = True
                    elif stripped.startswith("NEO4J_PASSWORD="):
                        env_lines.append(f"NEO4J_PASSWORD={passw}\n")
                        keys_found["NEO4J_PASSWORD"] = True
                    else:
                        env_lines.append(line)
        except Exception:
            pass

    if not keys_found["NEO4J_URI"]:
        env_lines.append(f"NEO4J_URI={uri}\n")
    if not keys_found["NEO4J_USER"]:
        env_lines.append(f"NEO4J_USER={user}\n")
    if not keys_found["NEO4J_PASSWORD"]:
        env_lines.append(f"NEO4J_PASSWORD={passw}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)
        print(f"📄 Konfigurasi kredensial berhasil disimpan di: {env_path.name}")
    except Exception as e:
        print(f"{YELLOW}{SYM_WARN} Gagal menyimpan ke .env: {e}{RESET}")

    # Sinkronisasi ke runtime environment
    os.environ["NEO4J_URI"] = uri
    os.environ["NEO4J_USER"] = user
    os.environ["NEO4J_PASSWORD"] = passw


def start_docker_neo4j(user: str = "neo4j", passw: str = "memoriagraph_pass", dry_run: bool = False) -> bool:
    """Menjalankan container Neo4j di Docker untuk Local Mode."""
    container_name = "memoriagraph-neo4j"
    print(f"\n{SYM_DOCKER} Memeriksa container Neo4j di Docker...")

    if dry_run:
        print(f"  [DRY RUN] Would start container '{container_name}' with user '{user}'")
        return True

    # Cek apakah container sudah ada
    res = subprocess.run(["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                         stdout=subprocess.PIPE, text=True)
    existing = res.stdout.strip()

    if container_name in existing.splitlines():
        print(f"  Container '{container_name}' ditemukan. Menyalakan container...")
        subprocess.run(["docker", "start", container_name], check=True)
    else:
        print(f"  Membuat dan menjalankan container '{container_name}' dengan user '{user}'...")
        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", "7687:7687",
            "-p", "7474:7474",
            "-e", f"NEO4J_AUTH={user}/{passw}",
            "-e", "NEO4J_PLUGINS=[\"apoc\"]",
            "-v", "memoriagraph_neo4j_data:/data",
            "neo4j:5-community"
        ]
        subprocess.run(run_cmd, check=True)

    print(f"  Menunggu database Neo4j siap menerima koneksi", end="", flush=True)
    for _ in range(15):
        if test_neo4j_socket("127.0.0.1", 7687):
            print(f" {GREEN}{SYM_OK}{RESET}")
            return True
        time.sleep(1)
        print(".", end="", flush=True)

    print(f" {YELLOW}Timeout, melanjutkan pengecekan...{RESET}")
    return test_neo4j_socket("127.0.0.1", 7687)


# =====================================================================
# 🌐 UNIVERSAL MULTI-AI ASSISTANT & MCP CLIENT INTEGRATION
# =====================================================================

def get_ai_clients(uri: str = None,
                   user: str = None, passw: str = None) -> dict[str, dict]:
    """Mengembalikan registry AI Assistant & IDE yang didukung untuk koneksi MCP."""
    target_uri = uri or os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
    target_user = user or os.environ.get("NEO4J_USER", "neo4j")
    target_pass = passw or os.environ.get("NEO4J_PASSWORD", "memoriagraph_pass")
    is_win = sys.platform == "win32"
    app_data = Path(os.getenv("APPDATA", "")) if is_win else Path.home()
    venv_py = get_venv_python().resolve()
    repo_dir = ROOT_DIR.resolve()

    mcp_entry = {
        "command": str(venv_py),
        "args": ["-m", "server"],
        "cwd": str(repo_dir),
        "env": {
            "PYTHONIOENCODING": "utf-8",
            "NEO4J_URI": target_uri,
            "NEO4J_USER": target_user,
            "NEO4J_PASSWORD": target_pass
        }
    }

    if is_win:
        claude_path = app_data / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "darwin":
        claude_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        claude_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    antigravity_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
    cursor_path = Path.home() / ".cursor" / "mcp.json"
    vscode_path = repo_dir / ".vscode" / "mcp.json"
    windsurf_path = Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    return {
        "antigravity": {
            "name": "Google Antigravity",
            "path": antigravity_path,
            "desc": "Google DeepMind Advanced Agentic Assistant",
            "detected": (Path.home() / ".gemini").exists(),
            "entry": mcp_entry
        },
        "claude": {
            "name": "Claude Desktop",
            "path": claude_path,
            "desc": "Anthropic Claude Desktop MCP Client",
            "detected": claude_path.parent.exists(),
            "entry": mcp_entry
        },
        "cursor": {
            "name": "Cursor IDE",
            "path": cursor_path,
            "desc": "Cursor AI Code Editor (Global)",
            "detected": (Path.home() / ".cursor").exists(),
            "entry": mcp_entry
        },
        "vscode": {
            "name": "VS Code & GitHub Copilot",
            "path": vscode_path,
            "desc": "Workspace MCP Configuration (.vscode/mcp.json)",
            "detected": (repo_dir / ".vscode").exists() or shutil.which("code") is not None,
            "entry": mcp_entry
        },
        "windsurf": {
            "name": "Windsurf IDE",
            "path": windsurf_path,
            "desc": "Codeium Windsurf AI Code Editor",
            "detected": (Path.home() / ".codeium" / "windsurf").exists(),
            "entry": mcp_entry
        }
    }


def sync_mcp_config(cfg_path: Path, mcp_entry: dict, client_name: str, dry_run: bool = False) -> bool:
    """Menginjeksi atau memperbarui entry memoriagraph di file konfigurasi MCP target secara aman."""
    print(f"\n{SYM_AI} {BOLD}Konfigurasi {client_name} MCP:{RESET}")
    print(f"  Target File: {cfg_path}")

    if dry_run:
        print(f"  [DRY RUN] Snippet konfigurasi:\n{json.dumps({'mcpServers': {'memoriagraph': mcp_entry}}, indent=2)}")
        return True

    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = {}
        if cfg_path.exists():
            try:
                # Backup file lama
                bak_path = cfg_path.with_suffix(f".bak.{int(time.time())}")
                shutil.copy2(cfg_path, bak_path)
                print(f"  Backup konfigurasi lama: {bak_path.name}")
                with open(cfg_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, dict):
                        config_data = content
            except Exception as e:
                print(f"  {SYM_WARN} Catatan: file lama tidak valid ({e}), membuat struktur baru.")
                config_data = {}

        if "mcpServers" not in config_data or not isinstance(config_data["mcpServers"], dict):
            config_data["mcpServers"] = {}

        config_data["mcpServers"]["memoriagraph"] = mcp_entry

        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        print(f"  {GREEN}{SYM_OK} {client_name} berhasil dikonfigurasi!{RESET}")
        return True
    except Exception as e:
        print(f"  {RED}{SYM_FAIL} Gagal mengonfigurasi {client_name}: {e}{RESET}")
        return False


def configure_claude_desktop(dry_run: bool = False, uri: str = "bolt://127.0.0.1:7687",
                             user: str = "neo4j", passw: str = "memoriagraph_pass") -> bool:
    """Shortcut backward-compatible untuk konfigurasi Claude Desktop."""
    clients = get_ai_clients(uri=uri, user=user, passw=passw)
    claude = clients.get("claude")
    if claude:
        return sync_mcp_config(claude["path"], claude["entry"], claude["name"], dry_run=dry_run)
    return False


def sync_all_ai_clients(dry_run: bool = False, uri: str = "bolt://127.0.0.1:7687",
                        user: str = "neo4j", passw: str = "memoriagraph_pass") -> list[str]:
    """Menghubungkan MemoriaGraph ke seluruh AI client dan IDE yang terdeteksi di sistem."""
    clients = get_ai_clients(uri=uri, user=user, passw=passw)
    connected = []
    print(f"\n{BOLD}{SYM_AI} Menjalankan Sinkronisasi Universal Multi-AI...{RESET}")

    for key, c in clients.items():
        if c["detected"]:
            ok = sync_mcp_config(c["path"], c["entry"], c["name"], dry_run=dry_run)
            if ok:
                connected.append(c["name"])

    # Juga selalu buat workspace-level configs (.vscode & .cursor) agar project portable
    for ws_key, ws_name in [("vscode", "VS Code Workspace"), ("cursor", "Cursor Workspace")]:
        ws_path = ROOT_DIR / f".{ws_key.lower()}" / "mcp.json"
        if ws_name not in connected:
            sync_mcp_config(ws_path, clients[ws_key]["entry"], ws_name, dry_run=dry_run)
            connected.append(ws_name)

    return connected


def show_chatgpt_and_rest_guide():
    """Menampilkan panduan integrasi untuk ChatGPT, OpenAI GPTs, dan REST API clients."""
    print(f"\n{CYAN}{BORDER_SUB}")
    print(f"{SYM_AI} INTEGRASI CHATGPT, OPENAI GPTs & REST API")
    print(f"{BORDER_SUB}{RESET}")
    print("""
Untuk menghubungkan MemoriaGraph ke ChatGPT Web / Custom GPT / n8n / Agents:

1. Jalankan MemoriaGraph HTTP Microservice (Port 8085):
   python http_service.py   (atau jalankan via Docker Compose)

2. ChatGPT Custom Actions (OpenAPI Schema):
   • Buka editor Custom GPT Anda di ChatGPT
   • Masukkan URL Schema berikut pada tab Actions:
     http://localhost:8085/openapi.json

3. Endpoints REST API Langsung:
   • Recall Memory : GET  http://localhost:8085/recall?query=database+issue&compact=true
   • Ingest Memory : POST http://localhost:8085/retain
     Payload: {"content": "Solusi bug auth", "bank_id": "codebase", "title": "Auth Fix"}
   • Health Check  : GET  http://localhost:8085/health
   • Cyber Cockpit : http://localhost:8085/cockpit
""")
    safe_input("Tekan Enter untuk kembali ke menu...")


def manage_ai_menu(dry_run: bool = False):
    """Sub-menu interaktif untuk memilih dan mengonfigurasi AI assistants & IDEs."""
    clients = get_ai_clients()
    while True:
        print(f"\n{CYAN}{BORDER_SUB}")
        print(f"{SYM_AI} SINKRONISASI AI ASSISTANT & MCP CLIENTS")
        print(f"{BORDER_SUB}{RESET}")
        print("Pilih AI Assistant atau IDE yang ingin Anda hubungkan:\n")

        keys = list(clients.keys())
        for idx, k in enumerate(keys, 1):
            c = clients[k]
            status = f"{GREEN}[TERDETEKSI]{RESET}" if c["detected"] else f"{YELLOW}[TERSEDIA]{RESET}"
            print(f" [{idx}] {BOLD}{c['name']:<25}{RESET} {status} ({c['desc']})")

        print(f"\n [{BOLD}A{RESET}] {GREEN}HUBUNGKAN SEMUA CLIENT TERDETEKSI SEKALIGUS (1-Click Universal Sync){RESET}")
        print(f" [{BOLD}R{RESET}] {YELLOW}Pasang Proactive Autonomous Rules ke AI Assistants (Zero-Prompt Auto-Use){RESET}")
        print(f" [{BOLD}C{RESET}] {CYAN}Panduan ChatGPT Custom GPT, OpenAI & REST API (Port 8085){RESET}")
        print(f" [{BOLD}B{RESET}] Kembali ke Menu Utama")

        pilihan = safe_input("\nMasukkan pilihan Anda [1-5/A/R/C/B]: ").upper()

        if pilihan == "A":
            sync_all_ai_clients(dry_run=dry_run)
            safe_input("\nTekan Enter untuk kembali ke menu...")
            break
        elif pilihan == "R":
            install_proactive_agent_rules(ROOT_DIR, dry_run=dry_run)
            safe_input("\nTekan Enter untuk kembali ke menu...")
        elif pilihan == "C":
            show_chatgpt_and_rest_guide()
        elif pilihan == "B":
            break
        elif pilihan.isdigit() and 1 <= int(pilihan) <= len(keys):
            target_key = keys[int(pilihan) - 1]
            c = clients[target_key]
            sync_mcp_config(c["path"], c["entry"], c["name"], dry_run=dry_run)
            safe_input("\nTekan Enter untuk kembali ke menu...")
        else:
            print("Pilihan tidak valid, silakan coba lagi.")
            time.sleep(1)


def setup_windows_startup(dry_run: bool = False) -> bool:
    """Menambahkan silent shortcut Cockpit Tray ke folder Startup Windows."""
    if sys.platform != "win32":
        print(f"ℹ️ Opsi Startup Taskbar Tray saat ini khusus untuk Windows.")
        return False

    app_data = os.getenv("APPDATA")
    if not app_data:
        return False

    startup_dir = Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    vbs_src = ROOT_DIR / "scripts" / "start_cockpit_silent.vbs"
    target_link = startup_dir / "MemoriaGraphCockpit.vbs"

    print(f"\n{SYM_TRAY} Menyiapkan Auto-Startup Cockpit di Taskbar:")
    print(f"  Target: {target_link}")

    if dry_run:
        print(f"  [DRY RUN] Would copy {vbs_src} to {target_link}")
        return True

    try:
        shutil.copy2(vbs_src, target_link)
        print(f"{GREEN}{SYM_OK} Cockpit berhasil didaftarkan ke Windows Startup!{RESET}")
        print(f"{SYM_INFO} Setiap kali PC dinyalakan, Cockpit otomatis standby di Taskbar tanpa jendela terminal hitam.")
        return True
    except Exception as e:
        print(f"{YELLOW}{SYM_WARN} Gagal mendaftarkan ke Startup: {e}{RESET}")
        return False


PROACTIVE_RULES_CONTENT = """# 🧠 MemoriaGraph 3.2.0 - Proactive Cognitive Memory Protocol
<!-- Autonomously generated by MemoriaGraph Universal Installer -->
You have access to MemoriaGraph, an external sovereign cognitive memory substrate via MCP tools (`recall`, `retain`, `reflect`).

## 🚨 MANDATORY AUTONOMOUS COGNITIVE PROTOCOL:

1. **PROACTIVE RECALL (Pre-Action / Zero-Prompt)**:
   - At the beginning of ANY non-trivial engineering task, bug investigation, architecture planning, or user question, ALWAYS call `recall(query="...", bank_id="...")` FIRST.
   - Retrieve relevant past precedents, codebase AST blast-radii, architectural decisions, and known heuristics before proposing solutions or modifying files.
   - DO NOT wait for the user to explicitly ask "check memory" or "search memoriagraph".

2. **PROACTIVE RETAIN (Post-Action Persistence)**:
   - Immediately upon successfully resolving a bug, completing a feature, or formulating a tested engineering heuristic, ALWAYS call `retain(content="...", title="...", bank_id="...", outcome_status="SUCCESS")`.
   - Never let hard-won problem-solving insights disappear when the conversation context truncates or ends.

3. **DYNAMIC MEMORY BANK ROUTING**:
   - Route memories to their correct dynamic bank:
     - `codebase`: Code refactors, AST changes, bugfixes, and git modifications.
     - `operations`: Docker, server topologies, system configurations, and monitoring.
     - `research`: Emerging tech, benchmarks, evaluations, and prototypes.
     - `general`: General conversation context and cross-domain heuristics.

4. **ZERO-SECRET SECURITY FIRST**:
   - NEVER ingest raw passwords, private keys, or unmasked bearer tokens. MemoriaGraph sanitizes content, but agents must practice defense-in-depth by redacting secrets before calling `retain`.
"""


def install_proactive_agent_rules(workspace_dir: Path = None, dry_run: bool = False) -> list[str]:
    """
    Menginjeksi aturan kognitif proaktif ke Cursor, Copilot, Windsurf, dan Antigravity
    agar AI Assistant otomatis memanggil recall & retain tanpa perlu disuruh user.
    """
    if workspace_dir is None:
        workspace_dir = ROOT_DIR

    print(f"\n{CYAN}{BORDER_SUB}")
    print(f"🤖 INJEKSI ATURAN PROAKTIF AI (ZERO-PROMPT AUTONOMOUS MODE)")
    print(f"{BORDER_SUB}{RESET}")
    print(f"Menyiapkan aturan kognitif di workspace: {BOLD}{workspace_dir}{RESET}\n")

    targets = [
        # Cursor IDE Modern Rules
        workspace_dir / ".cursor" / "rules" / "memoriagraph.mdc",
        # VS Code & GitHub Copilot Workspace Instructions
        workspace_dir / ".github" / "copilot-instructions.md",
        # Windsurf IDE Workspace Rules
        workspace_dir / ".windsurfrules",
        # Google Antigravity Global Agent Rules
        Path.home() / ".gemini" / "config" / "rules" / "memoriagraph.md",
    ]

    installed = []
    for target in targets:
        rel = target.relative_to(workspace_dir) if str(target).startswith(str(workspace_dir)) else target
        print(f"• Target: {rel}...", end=" ")
        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET}")
            installed.append(str(target))
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                existing = target.read_text(encoding="utf-8", errors="ignore")
                if "MemoriaGraph" not in existing:
                    target.write_text(existing.rstrip() + "\n\n" + PROACTIVE_RULES_CONTENT, encoding="utf-8")
                    print(f"{GREEN}[DIPERBARUI]{RESET}")
                else:
                    print(f"{GREEN}[AKTIF]{RESET}")
            else:
                target.write_text(PROACTIVE_RULES_CONTENT, encoding="utf-8")
                print(f"{GREEN}[DIBUAT]{RESET}")
            installed.append(str(target))
        except Exception as e:
            print(f"{RED}[GAGAL: {e}]{RESET}")

    print(f"\n{GREEN}{SYM_OK} Proactive Memory Rules berhasil dipasang ke {len(installed)} lokasi!{RESET}")
    print("💡 Sekarang Cursor, Copilot, Antigravity, dan Windsurf akan otomatis:")
    print("   1. Auto-Recall memori saat Anda bertanya atau meminta coding.")
    print("   2. Auto-Retain solusi saat berhasil menyelesaikan masalah.")
    return installed


def run_local_mode(dry_run: bool = False):
    """Menjalankan alur lengkap Local Mode (PC/Laptop untuk Claude Desktop / Cursor)."""
    print_banner()
    print(f"{BOLD}[*] MENJALANKAN MODE 1: LOCAL SETUP (AI Assistants + Docker Neo4j){RESET}")
    print("━" * 65)

    # 1. Cek Python & Virtualenv
    if not check_python_version():
        return
    venv_py = ensure_virtualenv(dry_run=dry_run)

    # 2. Konfigurasi Kredensial Neo4j
    neo_uri = "bolt://127.0.0.1:7687"
    neo_user, neo_pass = prompt_neo4j_credentials()
    save_env_credentials(neo_uri, neo_user, neo_pass)

    print(f"\n{SYM_SEARCH} Memeriksa koneksi Neo4j di {neo_uri}...", end=" ")
    is_live = test_neo4j_socket("127.0.0.1", 7687)

    if is_live:
        print(f"{GREEN}AKTIF!{RESET}")
    else:
        print(f"{YELLOW}OFFLINE!{RESET}")
        if is_docker_available():
            print(f"{SYM_DOCKER} {GREEN}Docker terdeteksi aktif di sistem ini!{RESET}")
            resp = safe_input(f"Ingin menjalankan Neo4j di Docker secara otomatis dengan user '{neo_user}'? [Y/n]: ").lower()
            if resp in ("", "y", "yes"):
                start_docker_neo4j(user=neo_user, passw=neo_pass, dry_run=dry_run)
        else:
            print(f"{YELLOW}{SYM_WARN} Docker tidak terdeteksi. Pastikan Neo4j Desktop / Server sudah berjalan di port 7687.{RESET}")

    # 3. Inisialisasi Skema Neo4j
    print(f"\n{SYM_BRAIN} Menginisialisasi Skema Graph & Fulltext Indexes di Neo4j...")
    if not dry_run:
        try:
            init_cmd = [str(venv_py), "-c", "from src.schema_init import init_schema; init_schema()"]
            subprocess.run(init_cmd, cwd=str(ROOT_DIR), check=True)
        except Exception as e:
            print(f"{YELLOW}{SYM_WARN} Inisialisasi skema dilewati / selesai dengan catatan: {e}{RESET}")

    # 4. Hubungkan ke AI Assistant & IDE
    print(f"\n{BOLD}{SYM_AI} LANGKAH 4: HUBUNGKAN KE AI ASSISTANT & IDE{RESET}")
    print(f"Pilih integrasi yang Anda butuhkan:")
    print(f" [{BOLD}A{RESET}] {GREEN}Hubungkan SEMUA yang Terdeteksi (Rekomendasi: Antigravity, Claude, Cursor, Copilot){RESET}")
    print(f" [1] Google Antigravity")
    print(f" [2] Claude Desktop")
    print(f" [3] Cursor IDE")
    print(f" [4] VS Code & GitHub Copilot")
    print(f" [5] Windsurf IDE")
    print(f" [S] Lewati (Atur nanti)")

    ai_choice = safe_input(f"Pilihan Anda [A/1-5/S, default: A]: ").upper() or "A"
    if ai_choice == "A":
        sync_all_ai_clients(dry_run=dry_run, uri=neo_uri, user=neo_user, passw=neo_pass)
    elif ai_choice in ("1", "2", "3", "4", "5"):
        ai_keys = ["antigravity", "claude", "cursor", "vscode", "windsurf"]
        chosen_key = ai_keys[int(ai_choice) - 1]
        clients = get_ai_clients(uri=neo_uri, user=neo_user, passw=neo_pass)
        c = clients[chosen_key]
        sync_mcp_config(c["path"], c["entry"], c["name"], dry_run=dry_run)

    # 5. Pasang Proactive Rules ke AI Assistants
    resp_rules = safe_input(f"\n{SYM_BRAIN} Ingin memasang Proactive Rules agar AI (Cursor, Antigravity, Copilot, Windsurf) otomatis membaca & menyimpan memori tanpa disuruh? [Y/n]: ").lower()
    if resp_rules in ("", "y", "yes"):
        install_proactive_agent_rules(ROOT_DIR, dry_run=dry_run)

    # 6. Opsi Taskbar Tray & Startup Windows
    if sys.platform == "win32":
        resp_tray = safe_input(f"\n{SYM_TRAY} Ingin Cockpit otomatis berjalan di Taskbar saat Windows dinyalakan? [Y/n]: ").lower()
        if resp_tray in ("", "y", "yes"):
            setup_windows_startup(dry_run=dry_run)

    print(f"\n{GREEN}{BORDER}")
    print(f"{SYM_SUCCESS} INSTALASI LOCAL MODE SELESAI DENGAN SUKSES!")
    print(f"{BORDER}{RESET}")
    print(f"• AI Assistants : Antigravity, Claude Desktop, Cursor, Copilot siap digunakan")
    print(f"• Cybernetic UI : Buka 'scripts/cockpit_tray.py' untuk taskbar icon")
    print(f"• Web Cockpit   : http://localhost:8085 (jika service aktif)\n")


def run_server_mode(dry_run: bool = False):
    """Menjalankan alur lengkap Server Mode (Docker Compose)."""
    print_banner()
    print(f"{BOLD}▶️ MENJALANKAN MODE 2: SERVER SETUP (Docker Compose Stack){RESET}")
    print("━" * 65)

    if not is_docker_available():
        print(f"{RED}{SYM_FAIL} Docker daemon tidak terdeteksi. Silakan instal atau jalankan Docker Desktop terlebih dahulu.{RESET}")
        return

    # Atur kredensial kustom untuk compose
    neo_user, neo_pass = prompt_neo4j_credentials()
    save_env_credentials("bolt://127.0.0.1:7687", neo_user, neo_pass)

    print(f"\n{SYM_DOCKER} Menjalankan seluruh stack (Neo4j + MemoriaGraph HTTP Microservice)...")
    cmd = ["docker", "compose", "up", "-d"]
    if dry_run:
        print(f"  [DRY RUN] Would execute: {' '.join(cmd)}")
        return

    try:
        subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
        print(f"\n{GREEN}{SYM_OK} Seluruh container berhasil dijalankan di background!{RESET}")
        print(f"• Web Cockpit & REST API : http://localhost:8085")
        print(f"• Neo4j Browser UI      : http://localhost:7474 (user: {neo_user})")
        print(f"• Neo4j Bolt Gateway     : bolt://localhost:7687")
        print(f"• OpenAPI Schema (GPT)  : http://localhost:8085/openapi.json")
    except Exception as e:
        print(f"{SYM_FAIL} Gagal menjalankan Docker Compose: {e}")


def interactive_menu():
    """Menu interaktif utama untuk pengguna awam."""
    while True:
        print_banner()
        print("Pilih tipe instalasi yang Anda butuhkan:\n")
        print(f" {BOLD}[1]{RESET} {SYM_LOCAL} {GREEN}LOCAL MODE (Rekomendasi Laptop/PC){RESET}")
        print("     -> Untuk Antigravity, Claude Desktop, Cursor, Copilot & Tray.")
        print("     -> Neo4j di Docker, MemoriaGraph di Host.")
        print("     -> Otomatis hubungkan ke AI Assistant tanpa edit JSON!\n")
        print(f" {BOLD}[2]{RESET} {SYM_SERVER} {CYAN}SERVER MODE (Production / Headless){RESET}")
        print("     -> Untuk Server, VM, n8n, Multi-Agent, ChatGPT & Web Cockpit.")
        print("     -> Menjalankan Neo4j + MemoriaGraph HTTP di Docker Compose.\n")
        print(f" {BOLD}[3]{RESET} {SYM_TRAY}  Setup Taskbar Tray & Auto-Startup Windows Saja")
        print(f" {BOLD}[4]{RESET} {SYM_BANKS} Kelola Kategori Memory Bank (Tambah/Hapus bank_id)")
        print(f" {BOLD}[5]{RESET} {SYM_AI} Hubungkan AI Assistant (Antigravity, Claude, Cursor, Copilot, Windsurf)")
        print(f" {BOLD}[6]{RESET} {SYM_BRAIN} Pasang Proactive Rules ke AI Assistants (Zero-Prompt Auto-Use)")
        print(f" {BOLD}[0]{RESET} Keluar\n")

        pilihan = safe_input("Masukkan pilihan Anda [1/2/3/4/5/6/0]: ")

        if pilihan == "1":
            run_local_mode()
            break
        elif pilihan == "2":
            run_server_mode()
            break
        elif pilihan == "3":
            setup_windows_startup()
            safe_input("\nTekan Enter untuk kembali ke menu...")
        elif pilihan == "4":
            manage_banks_menu()
        elif pilihan == "5":
            manage_ai_menu()
        elif pilihan == "6":
            install_proactive_agent_rules(ROOT_DIR)
            safe_input("\nTekan Enter untuk kembali ke menu...")
        elif pilihan == "0":
            print("Keluar dari installer. Sampai jumpa!")
            break
        else:
            print("Pilihan tidak valid, silakan coba lagi.")
            time.sleep(1)


def manage_banks_menu():
    """Sub-menu untuk melihat, menambah, atau menghapus kategori memory bank."""
    while True:
        print(f"\n{CYAN}{BORDER_SUB}")
        print(f"{SYM_BANKS} KELOLA KATEGORI MEMORY BANK (banks.json)")
        print(f"{BORDER_SUB}{RESET}")
        banks = bank_manager.list_banks()
        for idx, b in enumerate(banks, 1):
            print(f" {idx}. {BOLD}{b['id']}{RESET}: {b['name']} ({b.get('description', '-')})")
        print("\n [A] Tambah Kategori Bank Baru")
        print(" [D] Hapus Kategori Bank")
        print(" [B] Kembali ke Menu Utama")

        act = safe_input("\nPilih aksi [A/D/B]: ").upper()
        if act == "A":
            bid = safe_input("ID Bank (contoh: marketing, devops): ")
            name = safe_input("Nama Kategori (contoh: Marketing Strategy): ")
            desc = safe_input("Deskripsi: ")
            kw = safe_input("Keywords (pisahkan koma): ")
            kw_list = [k.strip() for k in kw.split(",") if k.strip()]
            try:
                bank_manager.add_bank(bid, name, desc, kw_list)
                print(f"{GREEN}{SYM_OK} Bank '{bid}' berhasil ditambahkan!{RESET}")
            except Exception as e:
                print(f"{RED}{SYM_FAIL} Error: {e}{RESET}")
        elif act == "D":
            bid = safe_input("Masukkan ID Bank yang ingin dihapus: ")
            try:
                if bank_manager.remove_bank(bid):
                    print(f"{GREEN}{SYM_OK} Bank '{bid}' berhasil dihapus.{RESET}")
                else:
                    print(f"{YELLOW}{SYM_WARN} Bank '{bid}' tidak ditemukan.{RESET}")
            except Exception as e:
                print(f"{RED}{SYM_FAIL} Error: {e}{RESET}")
        elif act == "B":
            break


def main():
    parser = argparse.ArgumentParser(description=f"MemoriaGraph {VERSION} - Universal Installer")
    parser.add_argument("--mode", choices=["local", "server", "claude", "ai", "tray", "banks", "rules"],
                        help="Jalankan mode instalasi tertentu secara langsung")
    parser.add_argument("--dry-run", action="store_true", help="Uji coba instalasi tanpa mengubah konfigurasi sistem")

    args = parser.parse_args()

    if args.mode == "local":
        run_local_mode(dry_run=args.dry_run)
    elif args.mode == "server":
        run_server_mode(dry_run=args.dry_run)
    elif args.mode in ("claude", "ai"):
        manage_ai_menu(dry_run=args.dry_run)
    elif args.mode == "tray":
        setup_windows_startup(dry_run=args.dry_run)
    elif args.mode == "banks":
        manage_banks_menu()
    elif args.mode == "rules":
        install_proactive_agent_rules(ROOT_DIR, dry_run=args.dry_run)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()

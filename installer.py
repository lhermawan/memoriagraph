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
import shutil
import socket
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


def print_banner():
    print(f"\n{CYAN}{'═' * 65}")
    print(f"🧠 MEMORIAGRAPH v{VERSION} - UNIVERSAL MODULAR INSTALLER")
    print(f"{'═' * 65}{RESET}\n")


def check_python_version() -> bool:
    """Memastikan Python host memenuhi syarat minimal >= 3.10."""
    v = sys.version_info
    print(f"🔍 Memeriksa versi Python host: {v.major}.{v.minor}.{v.micro}...", end=" ")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"{RED}GAGAL!{RESET}")
        print(f"❌ MemoriaGraph membutuhkan Python 3.10 atau lebih baru.")
        return False
    print(f"{GREEN}OK!{RESET}")
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
        print(f"📦 Membuat virtual environment baru di {venv_dir}...")
        if not dry_run:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
            venv_python = get_venv_python()
            print(f"✅ Virtual environment berhasil dibuat.")

    print(f"📦 Memastikan dependensi utama terinstal...")
    if not dry_run:
        pip_cmd = [str(venv_python), "-m", "pip", "install", "-e", "."]
        try:
            subprocess.run(pip_cmd, cwd=str(ROOT_DIR), check=True)
            print(f"{GREEN}✅ Dependensi MemoriaGraph terverifikasi lengkap!{RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠️ Catatan instalasi pip: {e}{RESET}")

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


def start_docker_neo4j(dry_run: bool = False) -> bool:
    """Menjalankan container Neo4j di Docker untuk Local Mode."""
    container_name = "memoriagraph-neo4j"
    print(f"\n🐳 Memeriksa container Neo4j di Docker...")

    if dry_run:
        print(f"  [DRY RUN] Would start container '{container_name}'")
        return True

    # Cek apakah container sudah ada
    res = subprocess.run(["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                         stdout=subprocess.PIPE, text=True)
    existing = res.stdout.strip()

    if container_name in existing.splitlines():
        print(f"  Container '{container_name}' ditemukan. Menyalakan container...")
        subprocess.run(["docker", "start", container_name], check=True)
    else:
        print(f"  Membuat dan menjalankan container '{container_name}'...")
        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", "7687:7687",
            "-p", "7474:7474",
            "-e", "NEO4J_AUTH=neo4j/memoriagraph_pass",
            "-e", "NEO4J_PLUGINS=[\"apoc\"]",
            "-v", "memoriagraph_neo4j_data:/data",
            "neo4j:5-community"
        ]
        subprocess.run(run_cmd, check=True)

    print(f"  ⏳ Menunggu database Neo4j siap menerima koneksi", end="", flush=True)
    for _ in range(15):
        if test_neo4j_socket("127.0.0.1", 7687):
            print(f" {GREEN}SIAP!{RESET}")
            return True
        time.sleep(1)
        print(".", end="", flush=True)

    print(f" {YELLOW}Timeout, melanjutkan pengecekan...{RESET}")
    return test_neo4j_socket("127.0.0.1", 7687)


def get_claude_config_path() -> Path | None:
    """Menemukan letak file claude_desktop_config.json sesuai sistem operasi."""
    os_name = platform.system()
    if os_name == "Windows":
        app_data = os.getenv("APPDATA")
        if app_data:
            return Path(app_data) / "Claude" / "claude_desktop_config.json"
    elif os_name == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    return None


def configure_claude_desktop(dry_run: bool = False, uri: str = "bolt://127.0.0.1:7687",
                             user: str = "neo4j", passw: str = "memoriagraph_pass") -> bool:
    """Menginjeksi konfigurasi MCP MemoriaGraph ke Claude Desktop secara otomatis."""
    cfg_path = get_claude_config_path()
    if not cfg_path:
        print(f"{YELLOW}⚠️ Path Claude Desktop tidak dapat dideteksi di OS ini.{RESET}")
        return False

    venv_py = get_venv_python().resolve()
    repo_dir = ROOT_DIR.resolve()

    # Struktur mcpServers entry
    mcp_entry = {
        "command": str(venv_py),
        "args": ["server.py"],
        "cwd": str(repo_dir),
        "env": {
            "PYTHONIOENCODING": "utf-8",
            "NEO4J_URI": uri,
            "NEO4J_USER": user,
            "NEO4J_PASSWORD": passw
        }
    }

    print(f"\n🤖 {BOLD}Konfigurasi Claude Desktop MCP:{RESET}")
    print(f"  File Target: {cfg_path}")
    print(f"  Executable : {venv_py}")
    print(f"  Working Dir: {repo_dir}")

    if dry_run:
        print(f"  [DRY RUN] Snippet yang akan ditulis:\n{json.dumps({'mcpServers': {'memoriagraph': mcp_entry}}, indent=2)}")
        return True

    # Buat direktori jika belum ada
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"mcpServers": {}}
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict):
                    data = content
                    if "mcpServers" not in data:
                        data["mcpServers"] = {}
            # Backup file lama
            bak_path = cfg_path.with_suffix(".json.bak")
            shutil.copy2(cfg_path, bak_path)
            print(f"  📁 Backup dibuat di: {bak_path}")
        except Exception as e:
            print(f"  ⚠️ File config lama tidak valid ({e}), membuat struktur baru.")
            data = {"mcpServers": {}}

    data["mcpServers"]["memoriagraph"] = mcp_entry

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"{GREEN}✅ Claude Desktop berhasil dikonfigurasi secara otomatis!{RESET}")
    print(f"👉 {BOLD}Cukup Restart Claude Desktop Anda untuk mulai menggunakannya.{RESET}")
    return True


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

    print(f"\n🚀 Menyiapkan Auto-Startup Cockpit di Taskbar:")
    print(f"  Target: {target_link}")

    if dry_run:
        print(f"  [DRY RUN] Would copy {vbs_src} to {target_link}")
        return True

    try:
        shutil.copy2(vbs_src, target_link)
        print(f"{GREEN}✅ Cockpit berhasil didaftarkan ke Windows Startup!{RESET}")
        print(f"💡 Setiap kali PC dinyalakan, Cockpit otomatis standby di Taskbar tanpa jendela terminal hitam.")
        return True
    except Exception as e:
        print(f"⚠️ Gagal mendaftarkan ke Startup: {e}")
        return False


def run_local_mode(dry_run: bool = False):
    """Menjalankan alur lengkap Local Mode (PC/Laptop untuk Claude Desktop / Cursor)."""
    print_banner()
    print(f"{BOLD}▶️ MENJALANKAN MODE 1: LOCAL SETUP (Claude Desktop + Docker Neo4j){RESET}")
    print("━" * 65)

    # 1. Cek Python & Virtualenv
    if not check_python_version():
        return
    venv_py = ensure_virtualenv(dry_run=dry_run)

    # 2. Cek Neo4j
    neo_uri = "bolt://127.0.0.1:7687"
    neo_user = "neo4j"
    neo_pass = "memoriagraph_pass"

    print(f"\n🔍 Memeriksa koneksi Neo4j di {neo_uri}...", end=" ")
    is_live = test_neo4j_socket("127.0.0.1", 7687)

    if is_live:
        print(f"{GREEN}AKTIF!{RESET}")
    else:
        print(f"{YELLOW}OFFLINE!{RESET}")
        if is_docker_available():
            print(f"🐳 {GREEN}Docker terdeteksi aktif di sistem ini!{RESET}")
            resp = input(f"Ingin menjalankan Neo4j di Docker secara otomatis? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                start_docker_neo4j(dry_run=dry_run)
        else:
            print(f"⚠️ Docker tidak terdeteksi. Pastikan Neo4j Desktop / Server sudah berjalan di port 7687.")
            neo_pass = input(f"Masukkan password Neo4j Anda [default: {neo_pass}]: ").strip() or neo_pass

    # 3. Inisialisasi Skema Neo4j
    print(f"\n🧠 Menginisialisasi Skema Graph & Fulltext Indexes di Neo4j...")
    if not dry_run:
        try:
            init_cmd = [str(venv_py), "-c", "from src.schema_init import init_schema; init_schema()"]
            subprocess.run(init_cmd, cwd=str(ROOT_DIR), check=True)
        except Exception as e:
            print(f"{YELLOW}⚠️ Inisialisasi skema dilewati / selesai dengan catatan: {e}{RESET}")

    # 4. Hubungkan ke Claude Desktop
    configure_claude_desktop(dry_run=dry_run, uri=neo_uri, user=neo_user, passw=neo_pass)

    # 5. Opsi Taskbar Tray & Startup Windows
    if sys.platform == "win32":
        resp_tray = input(f"\n🚀 Ingin Cockpit otomatis berjalan di Taskbar saat Windows dinyalakan? [Y/n]: ").strip().lower()
        if resp_tray in ("", "y", "yes"):
            setup_windows_startup(dry_run=dry_run)

    print(f"\n{GREEN}{'═' * 65}")
    print(f"🎉 INSTALASI LOCAL MODE SELESAI DENGAN SUKSES!")
    print(f"{'═' * 65}{RESET}")
    print(f"• Claude Desktop : Siap digunakan (Restart Claude Desktop)")
    print(f"• Cybernetic UI  : Buka 'scripts/cockpit_tray.py' untuk taskbar icon")
    print(f"• Web Cockpit    : http://localhost:8085 (jika service aktif)\n")


def run_server_mode(dry_run: bool = False):
    """Menjalankan alur lengkap Server Mode (Docker Compose)."""
    print_banner()
    print(f"{BOLD}▶️ MENJALANKAN MODE 2: SERVER SETUP (Docker Compose Stack){RESET}")
    print("━" * 65)

    if not is_docker_available():
        print(f"{RED}❌ Docker daemon tidak terdeteksi. Silakan instal atau jalankan Docker Desktop terlebih dahulu.{RESET}")
        return

    print(f"🐳 Menjalankan seluruh stack (Neo4j + MemoriaGraph HTTP Microservice)...")
    cmd = ["docker", "compose", "up", "-d"]
    if dry_run:
        print(f"  [DRY RUN] Would execute: {' '.join(cmd)}")
        return

    try:
        subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
        print(f"\n{GREEN}✅ Seluruh container berhasil dijalankan di background!{RESET}")
        print(f"• 🌐 Web Cockpit & REST API : http://localhost:8085")
        print(f"• 🗄️ Neo4j Browser UI      : http://localhost:7474")
        print(f"• 🔌 Neo4j Bolt Gateway     : bolt://localhost:7687")
    except Exception as e:
        print(f"❌ Gagal menjalankan Docker Compose: {e}")


def interactive_menu():
    """Menu interaktif utama untuk pengguna awam."""
    while True:
        print_banner()
        print("Pilih tipe instalasi yang Anda butuhkan:\n")
        print(f" {BOLD}[1]{RESET} 💻 {GREEN}LOCAL MODE (Rekomendasi Laptop/PC){RESET}")
        print("     -> Untuk Claude Desktop, Cursor IDE & Taskbar Tray.")
        print("     -> Neo4j di Docker, MemoriaGraph di Host.")
        print("     -> Otomatis hubungkan ke Claude tanpa edit JSON!\n")
        print(f" {BOLD}[2]{RESET} 🌐 {CYAN}SERVER MODE (Production / Headless){RESET}")
        print("     -> Untuk Server, VM, n8n, Multi-Agent & Web Cockpit.")
        print("     -> Menjalankan Neo4j + MemoriaGraph HTTP di Docker Compose.\n")
        print(f" {BOLD}[3]{RESET} 🖥️  Setup Taskbar Tray & Auto-Startup Windows Saja")
        print(f" {BOLD}[4]{RESET} 🏦 Kelola Kategori Memory Bank (Tambah/Hapus bank_id)")
        print(f" {BOLD}[5]{RESET} 🔧 Repair / Sync Konfigurasi Claude Desktop Saja")
        print(f" {BOLD}[0]{RESET} Keluar\n")

        pilihan = input("Masukkan pilihan Anda [1/2/3/4/5/0]: ").strip()

        if pilihan == "1":
            run_local_mode()
            break
        elif pilihan == "2":
            run_server_mode()
            break
        elif pilihan == "3":
            setup_windows_startup()
            input("\nTekan Enter untuk kembali ke menu...")
        elif pilihan == "4":
            manage_banks_menu()
        elif pilihan == "5":
            configure_claude_desktop()
            input("\nTekan Enter untuk kembali ke menu...")
        elif pilihan == "0":
            print("Keluar dari installer. Sampai jumpa!")
            break
        else:
            print("Pilihan tidak valid, silakan coba lagi.")
            time.sleep(1)


def manage_banks_menu():
    """Sub-menu untuk melihat, menambah, atau menghapus kategori memory bank."""
    while True:
        print(f"\n{CYAN}{'═' * 50}")
        print("🏦 KELOLA KATEGORI MEMORY BANK (banks.json)")
        print(f"{'═' * 50}{RESET}")
        banks = bank_manager.list_banks()
        for idx, b in enumerate(banks, 1):
            print(f" {idx}. {BOLD}{b['id']}{RESET}: {b['name']} ({b.get('description', '-')})")
        print("\n [A] Tambah Kategori Bank Baru")
        print(" [D] Hapus Kategori Bank")
        print(" [B] Kembali ke Menu Utama")

        act = input("\nPilih aksi [A/D/B]: ").strip().upper()
        if act == "A":
            bid = input("ID Bank (contoh: marketing, devops): ").strip()
            name = input("Nama Kategori (contoh: Marketing Strategy): ").strip()
            desc = input("Deskripsi: ").strip()
            kw = input("Keywords (pisahkan koma): ").strip()
            kw_list = [k.strip() for k in kw.split(",") if k.strip()]
            try:
                bank_manager.add_bank(bid, name, desc, kw_list)
                print(f"{GREEN}✅ Bank '{bid}' berhasil ditambahkan!{RESET}")
            except Exception as e:
                print(f"{RED}❌ Error: {e}{RESET}")
        elif act == "D":
            bid = input("Masukkan ID Bank yang ingin dihapus: ").strip()
            try:
                if bank_manager.remove_bank(bid):
                    print(f"{GREEN}✅ Bank '{bid}' berhasil dihapus.{RESET}")
                else:
                    print(f"{YELLOW}⚠️ Bank '{bid}' tidak ditemukan.{RESET}")
            except Exception as e:
                print(f"{RED}❌ Error: {e}{RESET}")
        elif act == "B":
            break


def main():
    parser = argparse.ArgumentParser(description=f"MemoriaGraph {VERSION} - Universal Installer")
    parser.add_argument("--mode", choices=["local", "server", "claude", "tray", "banks"],
                        help="Jalankan mode instalasi tertentu secara langsung")
    parser.add_argument("--dry-run", action="store_true", help="Uji coba instalasi tanpa mengubah konfigurasi sistem")

    args = parser.parse_args()

    if args.mode == "local":
        run_local_mode(dry_run=args.dry_run)
    elif args.mode == "server":
        run_server_mode(dry_run=args.dry_run)
    elif args.mode == "claude":
        configure_claude_desktop(dry_run=args.dry_run)
    elif args.mode == "tray":
        setup_windows_startup(dry_run=args.dry_run)
    elif args.mode == "banks":
        manage_banks_menu()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()

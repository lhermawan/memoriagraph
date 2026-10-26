#!/usr/bin/env python3
"""
MemoriaGraph 3.2.0 - System Tray Companion (Taskbar Icon)
Memberikan akses 1-klik ke Cybernetic Cockpit di browser tanpa perlu membuka terminal console.
Mendukung Windows, macOS, dan Linux.
"""
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import ROOT_DIR

HTTP_PORT = int(os.getenv("MEMORIAGRAPH_HTTP_PORT", "8085"))
COCKPIT_URL = f"http://localhost:{HTTP_PORT}"

# Global subprocess handle
_server_process = None
_is_running = True

def create_tray_icon_image():
    """Membuat icon grafis 64x64 dinamis menggunakan Pillow."""
    try:
        from PIL import Image, ImageDraw
        # Buat gambar 64x64 RGBA transparan
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Background lingkaran cyan/biru neon
        draw.ellipse([4, 4, 60, 60], fill=(14, 165, 233, 240), outline=(2, 132, 199, 255), width=3)
        # Simpul graf di dalam (node & edge kognitif)
        draw.line([(20, 32), (32, 18)], fill=(255, 255, 255), width=3)
        draw.line([(32, 18), (44, 32)], fill=(255, 255, 255), width=3)
        draw.line([(20, 32), (32, 46)], fill=(255, 255, 255), width=3)
        draw.line([(44, 32), (32, 46)], fill=(255, 255, 255), width=3)
        draw.line([(32, 18), (32, 46)], fill=(255, 255, 255), width=2)
        # Titik-titik node
        for pt in [(20, 32), (32, 18), (44, 32), (32, 46)]:
            draw.ellipse([pt[0]-4, pt[1]-4, pt[0]+4, pt[1]+4], fill=(255, 255, 255))
        return img
    except Exception:
        # Fallback jika Pillow mengalami kendala
        from PIL import Image
        return Image.new("RGB", (64, 64), color=(14, 165, 233))

def start_cockpit_server():
    """Menjalankan http_service.py di subprocess terpisah tanpa jendela hitam terminal."""
    global _server_process
    if _server_process and _server_process.poll() is None:
        return  # Sudah berjalan

    cmd = [sys.executable, str(ROOT_DIR / "http_service.py")]
    
    # Flags untuk menyembunyikan console window di Windows
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000

    try:
        _server_process = subprocess.Popen(
            cmd,
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
    except Exception as e:
        print(f"Gagal menyalakan Cockpit: {e}", file=sys.stderr)

def stop_cockpit_server():
    """Menghentikan subprocess server."""
    global _server_process
    if _server_process and _server_process.poll() is None:
        try:
            _server_process.terminate()
            _server_process.wait(timeout=3)
        except Exception:
            try:
                _server_process.kill()
            except Exception:
                pass
        _server_process = None

def action_open_browser(icon=None, item=None):
    """Membuka Cockpit di browser default."""
    webbrowser.open(COCKPIT_URL)

def action_restart(icon=None, item=None):
    """Restart server Cockpit."""
    stop_cockpit_server()
    time.sleep(1)
    start_cockpit_server()
    if icon:
        try:
            icon.notify("MemoriaGraph Cockpit berhasil di-restart!", "Status Service")
        except Exception:
            pass

def action_exit(icon=None, item=None):
    """Hentikan service dan keluar dari tray."""
    global _is_running
    _is_running = False
    stop_cockpit_server()
    if icon:
        icon.stop()

def main():
    # 1. Pastikan server aktif di background
    start_cockpit_server()

    # 2. Coba import pystray
    try:
        import pystray
        from pystray import MenuItem as item, Menu
    except ImportError:
        # Jika pystray belum terpasang, coba pasang otomatis
        print("Memasang pystray untuk System Tray Companion...", file=sys.stderr)
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pystray"], check=True)
            import pystray
            from pystray import MenuItem as item, Menu
        except Exception as err:
            print(f"Pystray tidak tersedia ({err}). Membuka browser langsung...", file=sys.stderr)
            action_open_browser()
            # Loop pemantau sederhana
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_cockpit_server()
            return

    # 3. Setup Menu Tray
    icon_image = create_tray_icon_image()
    menu = Menu(
        item("🌐 Buka Cockpit (Browser)", action_open_browser, default=True),
        item("📊 Status: Running (Port 8085)", lambda i, it: None, enabled=False),
        Menu.SEPARATOR,
        item("🔄 Restart Service", action_restart),
        item("❌ Matikan & Keluar", action_exit),
    )

    icon = pystray.Icon(
        "MemoriaGraph",
        icon_image,
        "MemoriaGraph 3.2.0 - Cybernetic Cockpit",
        menu
    )

    print(f"🧠 MemoriaGraph 3.2.0 Taskbar Companion aktif. Buka: {COCKPIT_URL}", file=sys.stderr)
    
    # Jalankan pystray loop (blocking thread utama)
    icon.run()

if __name__ == "__main__":
    main()

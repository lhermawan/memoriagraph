#!/usr/bin/env python3
"""
MemoriaGraph 3.2.0 - Standalone Unified Test Runner
Menjalankan seluruh test suite unit secara cerdas (pytest jika ada, fallback ke unittest).
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

def main():
    print("=" * 65)
    print("🧪 MEMORIAGRAPH 3.2.0: UNIFIED TEST SUITE")
    print("=" * 65)

    # Cek apakah pytest tersedia
    try:
        import pytest
        has_pytest = True
    except ImportError:
        has_pytest = False

    if has_pytest:
        print("⚡ Menjalankan test via pytest runner...")
        exit_code = pytest.main(["-v", str(ROOT_DIR / "tests")])
        print("=" * 65)
        if exit_code == 0:
            print("🎉 SELURUH UNIT TEST LULUS 100%!")
            sys.exit(0)
        else:
            print(f"❌ Test runner selesai dengan exit code: {exit_code}")
            sys.exit(exit_code)
    else:
        print("⚡ Pytest tidak terdeteksi, menjalankan via unittest loader...")
        test_loader = unittest.TestLoader()
        test_suite = unittest.TestSuite()

        tests_dir = ROOT_DIR / "tests"
        discovered = test_loader.discover(start_dir=str(tests_dir), pattern="test_*.py")
        test_suite.addTests(discovered)

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)

        print("=" * 65)
        if result.wasSuccessful():
            print("🎉 SELURUH UNIT TEST LULUS 100%!")
            sys.exit(0)
        else:
            print(f"❌ {len(result.failures)} test gagal, {len(result.errors)} error.")
            sys.exit(1)

if __name__ == "__main__":
    main()

"""
Test Suite untuk Dynamic Memory Bank Manager (MemoriaGraph 3.2.0)
Menguji:
1. Inisialisasi default universal banks
2. Penambahan bank kustom
3. Proteksi bank default 'general' dari penghapusan
4. Penghapusan bank kustom
5. Slugify & normalisasi identifier
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bank_manager import BankManager


class TestBankManager(unittest.TestCase):
    def setUp(self):
        # Buat temporary file untuk isolasi tes
        self.tmp_fd, self.tmp_path = tempfile.mkstemp(suffix=".json")
        os.close(self.tmp_fd)
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)
        self.bm = BankManager(self.tmp_path)

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_default_banks_present(self):
        bank_ids = self.bm.get_bank_ids()
        self.assertIn("general", bank_ids)
        self.assertIn("codebase", bank_ids)
        self.assertIn("operations", bank_ids)
        self.assertIn("research", bank_ids)

    def test_add_custom_bank(self):
        new_b = self.bm.add_bank(
            bank_id="marketing-campaign",
            name="Marketing & Socials",
            description="Campaign tracking and public relations notes",
            keywords=["social", "ads", "growth"]
        )
        self.assertEqual(new_b["id"], "marketing-campaign")
        self.assertTrue(self.bm.is_valid_bank("marketing-campaign"))
        
        # Test persistence
        reloaded = BankManager(self.tmp_path)
        self.assertTrue(reloaded.is_valid_bank("marketing-campaign"))
        self.assertEqual(reloaded.get_bank("marketing-campaign")["name"], "Marketing & Socials")

    def test_protect_general_bank_deletion(self):
        with self.assertRaises(ValueError):
            self.bm.remove_bank("general")
        self.assertTrue(self.bm.is_valid_bank("general"))

    def test_remove_custom_bank(self):
        self.bm.add_bank("temporary-testing", name="Temp", description="Testing only")
        self.assertTrue(self.bm.is_valid_bank("temporary-testing"))

        removed = self.bm.remove_bank("temporary-testing")
        self.assertTrue(removed)
        self.assertFalse(self.bm.is_valid_bank("temporary-testing"))

    def test_slugify_and_normalize(self):
        self.assertEqual(self.bm.slugify("My Cool Bank!"), "my-cool-bank")
        self.assertEqual(self.bm.slugify("---test--case---"), "test-case")
        self.assertEqual(self.bm.slugify(""), "general")
        self.assertEqual(self.bm.slugify(None), "general")

        # Test normalize
        self.assertEqual(self.bm.normalize_bank_id("codebase"), "codebase")
        self.assertEqual(self.bm.normalize_bank_id(None), "general")


if __name__ == "__main__":
    unittest.main()

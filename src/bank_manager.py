"""
MemoriaGraph 3.2.0 - Universal Memory Bank Registry & Category Manager
Provides dynamic, decoupled management of memory bank categories:
- Public defaults: general, codebase, operations, research
- Custom addition, removal, and listing via CLI or Python API
- Zero hardcoded domain isolation, fully configurable per project
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from src.config import BANKS_FILE, ROOT_DIR

DEFAULT_BANKS = {
    "version": "3.2.0",
    "default_bank": "general",
    "banks": [
        {
            "id": "general",
            "name": "General Knowledge",
            "description": "General domain knowledge, freeform dialogue context, and miscellaneous notes",
            "keywords": ["general", "notes", "misc", "summary", "conversation"]
        },
        {
            "id": "codebase",
            "name": "Codebase & Architecture",
            "description": "Software architecture, bug fixes, refactoring, algorithms, and git code changes",
            "keywords": ["code", "refactor", "bug", "architecture", "git", "api", "function", "class", "patch"]
        },
        {
            "id": "operations",
            "name": "Operations & Infrastructure",
            "description": "DevOps, containerization, deployment, servers, networking, and system monitoring",
            "keywords": ["devops", "docker", "server", "deploy", "nginx", "k8s", "pm2", "service", "systemd", "tailscale", "monitoring"]
        },
        {
            "id": "research",
            "name": "Research & Prototypes",
            "description": "Exploratory technical research, paper evaluations, prototypes, and benchmark studies",
            "keywords": ["research", "paper", "experiment", "benchmark", "learning", "prototype", "evaluation", "testbed"]
        }
    ]
}


class BankManager:
    """Manages memory banks dynamically with JSON persistence and fallback safety."""

    def __init__(self, file_path: str | Path | None = None):
        self.file_path = Path(file_path or BANKS_FILE)
        self._cache: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "banks" in data:
                        self._cache = data
                        return
            except Exception as e:
                print(f"⚠️ [BankManager] Gagal membaca {self.file_path}: {e}, memulihkan default.", file=sys.stderr)

        # Fallback & create default if missing
        self._cache = json.loads(json.dumps(DEFAULT_BANKS))
        self._save()

    def _save(self) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ [BankManager] Gagal menyimpan ke {self.file_path}: {e}", file=sys.stderr)
            return False

    def list_banks(self) -> list[dict[str, Any]]:
        """Mengembalikan daftar seluruh memory bank yang aktif."""
        return list(self._cache.get("banks", []))

    def get_bank_ids(self) -> list[str]:
        """Mengembalikan list ID dari semua memory bank."""
        return [b["id"] for b in self.list_banks()]

    def get_bank(self, bank_id: str) -> dict[str, Any] | None:
        """Mengambil data detail sebuah memory bank berdasarkan ID."""
        clean_id = self.slugify(bank_id)
        for b in self.list_banks():
            if b.get("id") == clean_id:
                return b
        return None

    def is_valid_bank(self, bank_id: str) -> bool:
        """Memeriksa apakah bank_id terdaftar."""
        return self.get_bank(bank_id) is not None

    def add_bank(
        self,
        bank_id: str,
        name: str,
        description: str = "",
        keywords: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Menambahkan memory bank baru ke dalam registry.
        Jika sudah ada, informasinya akan diperbarui.
        """
        clean_id = self.slugify(bank_id)
        if not clean_id:
            raise ValueError("ID memory bank tidak valid.")

        clean_name = name.strip() or clean_id.replace("-", " ").title()
        clean_desc = description.strip() or f"Memory bank untuk konteks {clean_name}"
        clean_kw = [k.strip().lower() for k in keywords] if keywords else [clean_id]

        new_entry = {
            "id": clean_id,
            "name": clean_name,
            "description": clean_desc,
            "keywords": clean_kw
        }

        # Check existing
        banks = self._cache.setdefault("banks", [])
        updated = False
        for idx, b in enumerate(banks):
            if b.get("id") == clean_id:
                banks[idx] = new_entry
                updated = True
                break

        if not updated:
            banks.append(new_entry)

        self._save()
        return new_entry

    def remove_bank(self, bank_id: str) -> bool:
        """
        Menghapus memory bank dari registry.
        Bank default ('general') dilindungi dan tidak dapat dihapus.
        """
        clean_id = self.slugify(bank_id)
        if clean_id in ("general", self._cache.get("default_bank", "general")):
            raise ValueError("Bank default 'general' dilindungi dan tidak dapat dihapus.")

        banks = self._cache.get("banks", [])
        initial_len = len(banks)
        self._cache["banks"] = [b for b in banks if b.get("id") != clean_id]

        if len(self._cache["banks"]) < initial_len:
            self._save()
            return True
        return False

    def normalize_bank_id(self, bank_id: str | None) -> str:
        """
        Menormalisasi bank_id input pengguna:
        - Jika terdaftar, kembalikan ID tersebut.
        - Jika tidak terdaftar tetapi valid format string, otomatis fallback ke 'general'.
        """
        if not bank_id or not isinstance(bank_id, str):
            return self._cache.get("default_bank", "general")

        clean = self.slugify(bank_id)
        if self.is_valid_bank(clean):
            return clean

        return clean

    @staticmethod
    def slugify(bank_id: str | None) -> str:
        """Menghasilkan identifier bank yang aman dan seragam (lowercase, alphanumeric + hyphen)."""
        if not bank_id or not isinstance(bank_id, str):
            return "general"
        slug = re.sub(r'[^a-zA-Z0-9\-]+', '-', bank_id.strip().lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        return slug[:32] if slug else "general"

    def format_summary(self) -> str:
        """Ringkasan satu baris daftar bank aktif untuk prompt tool atau help text."""
        banks = self.list_banks()
        return ", ".join([f"'{b['id']}' ({b['name']})" for b in banks])


# Global singleton instance
bank_manager = BankManager()

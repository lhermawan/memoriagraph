"""
MemoriaGraph 3.2.0 - Comprehensive Audit & Regression Test Suite (MG-RESEARCH-2026-10-17)
Memvalidasi perbaikan P0 dan P1:
1. Episode Outcome Classification & Non-Bias Ingestion (P0-1)
2. Vector Cache Atomicity, Corruption Auto-Recovery & Stale Pruning (P0-2)
3. Temporal Noise Elimination from Hybrid RRF (P1-1)
4. Epistemic Grounding Quality Gate (P1-2)
5. Memory Bank Slugification & Isolation (P1-3)
6. Belief Revision Idempotency & Mathematical Boundaries
"""

import os
import pickle
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from server import infer_outcome_status
from src.belief_revision import (
    calculate_challenged_score,
    calculate_reinforced_score,
)
from src.hybrid_recall import HybridRecallEngine
from src.semantic_sanitizer import (
    classify_epistemic_grounding,
    slugify_bank_id,
)


class TestEpisodeOutcomeClassification(unittest.TestCase):
    """Memverifikasi perbaikan P0-1: Penghapusan asumsi hardcoded sukses."""

    def test_infer_outcome_status_success(self):
        res = infer_outcome_status(
            content="Pemasangan redis berhasil 100% dan lulus uat.",
            title="Deploy Redis",
        )
        self.assertEqual(res, "SUCCESS")

    def test_infer_outcome_status_failure(self):
        res = infer_outcome_status(
            content="Koneksi database timeout error 500 dan service crash.",
            title="Database Panic",
        )
        self.assertEqual(res, "FAILURE")

    def test_infer_outcome_status_attempts_failed(self):
        attempts = [
            {"number": 1, "status": "FAILED"},
            {"number": 2, "status": "FAILED"}
        ]
        res = infer_outcome_status(
            content="Mencoba restart service.",
            title="Troubleshooting",
            attempts_list=attempts
        )
        self.assertEqual(res, "FAILURE")

    def test_infer_outcome_status_partial(self):
        res = infer_outcome_status(
            content="Migrasi database berhasil sebagian tapi ada error pada index.",
            title="Partial Migration"
        )
        self.assertEqual(res, "PARTIAL")

    def test_infer_outcome_status_unknown_for_neutral_content(self):
        res = infer_outcome_status(
            content="Observasi port 8080 pada workstation maskii.",
            title="Monitoring Port"
        )
        self.assertEqual(res, "UNKNOWN")

    def test_infer_outcome_explicit_override(self):
        res = infer_outcome_status(
            content="Bebas teks apa saja",
            explicit_status="FAILURE"
        )
        self.assertEqual(res, "FAILURE")


class TestVectorCacheIntegrityAndRecovery(unittest.TestCase):
    """Memverifikasi perbaikan P0-2: Atomicity, auto-recovery, and fingerprint updates."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(self.temp_dir.name, "test_vector_cache.pkl")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_atomic_save_and_versioned_envelope(self):
        with patch("src.hybrid_recall.VECTOR_CACHE_FILE", self.cache_file), \
             patch("src.hybrid_recall.get_driver", return_value=None):
            engine = HybridRecallEngine(auto_sync_vectors=False)
            engine.vector_cache = {
                "node_1": {"title": "Node 1", "summary": "Sum 1", "vector": [0.1, 0.2]}
            }
            engine._save_vector_cache()

            self.assertTrue(os.path.exists(self.cache_file))
            with open(self.cache_file, "rb") as f:
                loaded = pickle.load(f)

            self.assertEqual(loaded.get("schema_version"), 2)
            self.assertEqual(loaded.get("node_count"), 1)
            self.assertIn("node_1", loaded.get("data", {}))
            self.assertIn("checksum", loaded)
            self.assertIsInstance(loaded["checksum"], str)

    def test_checksum_mismatch_triggers_isolation_and_recovery(self):
        with patch("src.hybrid_recall.VECTOR_CACHE_FILE", self.cache_file), \
             patch("src.hybrid_recall.get_driver", return_value=None):
            engine = HybridRecallEngine(auto_sync_vectors=False)
            engine.vector_cache = {
                "node_valid": {"title": "Valid", "summary": "Sum", "vector": [0.1]}
            }
            engine._save_vector_cache()

            # Tamper the envelope with a fake/mismatched checksum
            with open(self.cache_file, "rb") as f:
                envelope = pickle.load(f)
            envelope["checksum"] = "badc0ffee" * 4
            with open(self.cache_file, "wb") as f:
                pickle.dump(envelope, f)

            # Re-init engine; checksum mismatch must trigger auto-recovery
            new_engine = HybridRecallEngine(auto_sync_vectors=False)
            self.assertEqual(new_engine.vector_cache, {})
            corrupted_backups = [f for f in os.listdir(self.temp_dir.name) if ".corrupted." in f]
            self.assertTrue(len(corrupted_backups) >= 1)

    def test_corrupted_cache_auto_recovery(self):
        # Tulis data korup ke cache
        with open(self.cache_file, "wb") as f:
            f.write(b"CORRUPTED_GARBAGE_DATA_NOT_A_PICKLE")

        with patch("src.hybrid_recall.VECTOR_CACHE_FILE", self.cache_file), \
             patch("src.hybrid_recall.get_driver", return_value=None):
            engine = HybridRecallEngine(auto_sync_vectors=False)
            # Verifikasi engine tidak crash dan mereset cache
            self.assertEqual(engine.vector_cache, {})
            # Verifikasi file corrupt diisolasi dengan prefix .corrupted.
            corrupted_backups = [f for f in os.listdir(self.temp_dir.name) if ".corrupted." in f]
            self.assertTrue(len(corrupted_backups) >= 1)


class TestTemporalChannelNoiseElimination(unittest.TestCase):
    """Memverifikasi perbaikan P1-1: Eliminasi polusi 25 episode acak ke RRF."""

    def test_no_temporal_pollution_on_conceptual_query(self):
        with patch("src.hybrid_recall.get_driver", return_value=None):
            engine = HybridRecallEngine(auto_sync_vectors=False)
            mock_session = MagicMock()
            
            # Query konseptual tanpa kata tanggal
            res = engine._channel_temporal(mock_session, "interactive 3d hud Three.js")
            self.assertEqual(res, [])
            # Verifikasi session.run TIDAK dipanggil sama sekali
            mock_session.run.assert_not_called()

    def test_temporal_channel_activates_on_date_keywords(self):
        with patch("src.hybrid_recall.get_driver", return_value=None):
            engine = HybridRecallEngine(auto_sync_vectors=False)
            mock_session = MagicMock()
            mock_session.run.return_value.data.return_value = [{"title": "Agenda Hari Ini"}]
            
            res = engine._channel_temporal(mock_session, "agenda hari ini")
            self.assertEqual(len(res), 1)
            mock_session.run.assert_called_once()


class TestEpistemicGroundingQualityGate(unittest.TestCase):
    """Memverifikasi perbaikan P1-2: Anti-slop dan pencegahan false certainty."""

    def test_plain_tech_names_do_not_falsely_become_fact(self):
        # Menyebut nama tools saja tanpa telemetri empiris -> INFERENCE, bukan FACT
        label, score = classify_epistemic_grounding("Docker sering restart sendiri di node worker-prod.")
        self.assertEqual(label, "INFERENCE")
        self.assertLess(score, 0.90)

    def test_genuine_empirical_evidence_classified_as_fact(self):
        label, score = classify_epistemic_grounding("Container dihentikan pada port 8080 dengan exit code 0.")
        self.assertEqual(label, "FACT")
        self.assertGreaterEqual(score, 0.90)

    def test_speculation_words_classified_as_hypothesis(self):
        label, score = classify_epistemic_grounding("Mungkin penyebabnya adalah memory leak pada PM2.")
        self.assertEqual(label, "HYPOTHESIS")
        self.assertLessEqual(score, 0.45)


class TestBankSlugification(unittest.TestCase):
    """Memverifikasi perbaikan P1-3: Sanitasi nama memory bank."""

    def test_slugify_long_sentence_bank(self):
        raw = "migrasi bot notification di node worker-prod dari lib-a ke lib-b"
        slug = slugify_bank_id(raw)
        self.assertTrue(len(slug) <= 32)
        self.assertRegex(slug, r"^[a-z0-9\-]+$")

    def test_slugify_standard_banks(self):
        self.assertEqual(slugify_bank_id("infra-sre"), "infra-sre")
        self.assertEqual(slugify_bank_id("  AI-HUD  "), "ai-hud")
        self.assertEqual(slugify_bank_id(""), "general")
        self.assertEqual(slugify_bank_id(None), "general")


class TestBeliefRevisionMathBoundaries(unittest.TestCase):
    """Memverifikasi rumus matematika penguatan & pelemahan belief."""

    def test_reinforcement_logarithmic_dampening(self):
        s1, st1 = calculate_reinforced_score(current_evidence=1, current_counter=0, current_score=0.60)
        s2, st2 = calculate_reinforced_score(current_evidence=10, current_counter=0, current_score=0.85)
        # Delta pada bukti ke-10 harus jauh lebih kecil dari bukti ke-1
        delta1 = s1 - 0.60
        delta2 = s2 - 0.85
        self.assertGreater(delta1, delta2)

    def test_challenge_hysteresis(self):
        # Keyakinan dengan 10 bukti kuat tidak langsung runtuh ke <0.20
        s_challenged, st = calculate_challenged_score(current_evidence=10, current_counter=0, current_score=0.90)
        self.assertGreater(s_challenged, 0.70)
        self.assertNotEqual(st, "DEPRECATED")


if __name__ == "__main__":
    unittest.main()

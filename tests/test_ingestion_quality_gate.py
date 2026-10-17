"""
Unit Tests for MemoriaGraph Shared Memory Ingestion Quality Gate
Reference: docs/research/MEMORIAGRAPH-MEMORY-INGESTION-QUALITY-STANDARD.md
"""

import pytest
from src.ingestion_gate import (
    CanonicalOutcomeStatus,
    CanonicalRecordType,
    IngestionStatus,
    MemoryIngestionQualityGate,
    OutcomeApplicability,
    REASON_FLUFF_STRIPPED,
    REASON_NON_TASK_OUTCOME_NEUTRALIZED,
    REASON_SECRET_DETECTED,
    REASON_UNVERIFIED_SUCCESS_DOWNGRADED,
    compute_idempotency_fingerprint,
    detect_critical_secrets,
)


@pytest.fixture
def gate():
    return MemoryIngestionQualityGate(enforce=True)


class TestTranscriptNoiseAndSlopRemoval:
    """1. Transcript noise: AI throat-clearing & concluding fluff stripped."""

    def test_ai_throat_clearing_and_concluding_fluff_stripped(self, gate):
        raw_content = (
            "Tentu saja Bos! Berikut adalah hasil investigasi Nginx.\n"
            "Konfigurasi upstream proxy telah disesuaikan pada /etc/nginx/sites-available/default.\n"
            "Semoga ini membantu dan bermanfaat!"
        )
        res = gate.validate(
            content=raw_content,
            title="Tentu! Setup Nginx Upstream Proxy",
            bank_id="infra-sre",
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert "Tentu saja Bos!" not in res.sanitized_content
        assert "Semoga ini membantu" not in res.sanitized_content
        assert "Tentu!" not in res.sanitized_title
        assert REASON_FLUFF_STRIPPED in res.reason_codes


class TestSuccessEvidenceGrounding:
    """2. Success without artifact: Must be downgraded to UNKNOWN + NEEDS_MORE_EVIDENCE."""

    def test_success_without_artifact_downgraded_to_unknown(self, gate):
        content = "Saya sudah memperbaiki bug login tadi siang dan semuanya berjalan lancar dan beres."
        res = gate.validate(
            content=content,
            title="Perbaikan Bug Login Portal",
            bank_id="general",
            record_type="TASK",
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert res.outcome_status == CanonicalOutcomeStatus.UNKNOWN.value
        assert res.review_decision == "NEEDS_MORE_EVIDENCE"
        assert REASON_UNVERIFIED_SUCCESS_DOWNGRADED in res.reason_codes

    def test_success_with_genuine_empirical_evidence_accepted(self, gate):
        content = (
            "Refactor auth controller selesai dieksekusi.\n"
            "Evidence: commit 5b16592, exit code 0, status 200 OK pada endpoint /api/auth/login."
        )
        res = gate.validate(
            content=content,
            title="Refactor Auth Controller",
            bank_id="general",
            record_type="TASK",
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert res.outcome_status == CanonicalOutcomeStatus.SUCCESS.value
        assert res.review_decision == "SUCCESS"
        assert res.provenance == "ARTIFACT_VERIFIED"


class TestAttemptLifecycleAndFailureHandling:
    """3 & 4. Intermediate failure then verified fix vs evidenced final failure."""

    def test_failed_attempt_then_verified_fix_preserves_history_and_succeeds(self, gate):
        attempts = [
            {"number": 1, "action": "Restart pm2 service", "result": "CrashLoopBackOff", "status": "FAILED"},
            {"number": 2, "action": "Fix port binding in config.json", "result": "exit code 0, status 200", "status": "SUCCESS"}
        ]
        res = gate.validate(
            content="Troubleshooting PM2 daemon crash pada port 8080.",
            title="Fix PM2 CrashLoopBackOff",
            bank_id="infra-sre",
            record_type="TASK",
            attempts=attempts,
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert res.outcome_status == CanonicalOutcomeStatus.SUCCESS.value
        assert res.metadata["parsed_attempts_count"] == 2

    def test_evidenced_final_failure(self, gate):
        content = "Investigasi kegagalan memory allocation pada GPU RTX 3050. Error: CUDA out of memory, exit code 137."
        res = gate.validate(
            content=content,
            title="GPU OOM Exception Investigation",
            bank_id="ai-hud",
            record_type="INCIDENT",
            outcome_status="FAILURE"
        )
        assert res.valid is True
        assert res.outcome_status == CanonicalOutcomeStatus.FAILURE.value
        assert res.review_decision == "FAILURE"


class TestNonTaskOutcomeApplicability:
    """5. Observations, Plans, Preferences forced to outcome_applicable=NO and NOT_APPLICABLE."""

    @pytest.mark.parametrize("plan_word", ["Rencana", "Roadmap", "Agenda"])
    def test_plans_and_agendas_forced_not_applicable(self, gate, plan_word):
        res = gate.validate(
            content=f"{plan_word} riset arsitektur mesh network minggu depan.",
            title=f"{plan_word} Riset Mesh Network",
            bank_id="infra-sre",
            outcome_status="SUCCESS"  # Even if someone erroneously passes SUCCESS
        )
        assert res.valid is True
        assert res.record_type == CanonicalRecordType.PLAN.value
        assert res.outcome_applicable == OutcomeApplicability.NO.value
        assert res.outcome_status == CanonicalOutcomeStatus.NOT_APPLICABLE.value
        assert res.review_decision == "NOT_APPLICABLE"
        assert REASON_NON_TASK_OUTCOME_NEUTRALIZED in res.reason_codes

    def test_observation_forced_not_applicable(self, gate):
        res = gate.validate(
            content="Pemantauan telemetri RAM server vm-maskii berada di 4.2 GB konsisten.",
            title="Observasi Utilisasi RAM vm-maskii",
            bank_id="infra-sre",
            record_type="OBSERVATION",
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert res.outcome_applicable == OutcomeApplicability.NO.value
        assert res.outcome_status == CanonicalOutcomeStatus.NOT_APPLICABLE.value
        assert res.review_decision == "NOT_APPLICABLE"


class TestSecretBlockingAndSecurityHardening:
    """6 & 7. Secrets blocked before embedding and provenance handling."""

    def test_critical_private_key_triggers_quarantine_without_leak(self, gate):
        dangerous_payload = (
            "Berikut adalah private key SSH root server:\n"
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn\n"
            "-----END OPENSSH PRIVATE KEY-----"
        )
        res = gate.validate(
            content=dangerous_payload,
            title="Deploy SSH Key",
            bank_id="infra-sre"
        )
        assert res.valid is False
        assert res.status == IngestionStatus.QUARANTINED
        assert REASON_SECRET_DETECTED in res.reason_codes
        # Pastikan string private key tidak terbawa dalam sanitized content
        assert "b3BlbnNzaC1rZXktdjE" not in res.sanitized_content
        assert "[QUARANTINED" in res.sanitized_content

    def test_api_token_in_content_is_quarantined_without_leak(self, gate):
        content = "Konfigurasi bot Telegram menggunakan token=sk-ant-api03-1234567890abcdefghijklmn."
        res = gate.validate(
            content=content,
            title="Setup Bot Token",
            bank_id="general"
        )
        assert res.valid is False
        assert res.status == IngestionStatus.QUARANTINED
        assert "sk-ant-api03" not in res.sanitized_content
        assert "[QUARANTINED" in res.sanitized_content

    def test_already_redacted_content_is_accepted_safely(self, gate):
        content = (
            "Konfigurasi bot Telegram menggunakan token=[REDACTED_TOKEN]. "
            "Evidence: commit 5b16592, exit code 0."
        )
        res = gate.validate(
            content=content,
            title="Setup Bot Token Clean",
            bank_id="general",
            record_type="TASK",
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert res.status == IngestionStatus.ACCEPTED
        assert res.outcome_status == CanonicalOutcomeStatus.SUCCESS.value


class TestIdempotencyAndFingerprinting:
    """8. Idempotency: Fingerprint remains stable across repeated ingestions."""

    def test_idempotency_fingerprint_stability(self):
        fp1 = compute_idempotency_fingerprint(
            bank="infra-sre",
            record_type="TASK",
            title="Setup Nginx Reverse Proxy",
            content="Konfigurasi proxy_pass ke 127.0.0.1:8085."
        )
        fp2 = compute_idempotency_fingerprint(
            bank="infra-sre",
            record_type="TASK",
            title="Setup Nginx Reverse Proxy",
            content="Konfigurasi proxy_pass ke 127.0.0.1:8085."
        )
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256


class TestEdgeCasesAndRejections:
    """9 & 10. Low-value noise & empty inputs rejected."""

    def test_empty_or_too_short_content_rejected(self, gate):
        res = gate.validate(content="   ", title="Test")
        assert res.valid is False
        assert res.status == IngestionStatus.REJECTED


class TestServerRetainIngestionGateIntegration:
    """End-to-End integration testing of server.retain() with IngestionGate."""

    def test_retain_blocks_critical_secret_before_db_write(self):
        import server
        dangerous_payload = (
            "Kredensial root server:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA0Y1+5xL8...\n"
            "-----END RSA PRIVATE KEY-----"
        )
        msg = server.retain(
            content=dangerous_payload,
            title="Root SSH Key",
            bank_id="infra-sre"
        )
        assert "🚫 [IngestionGate: QUARANTINED]" in msg
        assert "Kredensial sensitif" in msg or "kredensial sensitif" in msg

    def test_retain_auto_neutralizes_plan_outcomes(self):
        import server
        msg = server.retain(
            content="Rencana implementasi zero trust mesh VPN minggu depan.",
            title="Rencana Mesh VPN Zero Trust",
            bank_id="infra-sre",
            outcome_status="SUCCESS"
        )
        assert "💾 [Retain]" in msg
        assert "Type: PLAN" in msg
        assert "Outcome: NOT_APPLICABLE" in msg

    def test_retain_downgrades_unverified_task_success(self):
        import server
        msg = server.retain(
            content="Saya sudah memperbaiki bug memory leak tadi pagi.",
            title="Fix Memory Leak",
            bank_id="infra-sre",
            outcome_status="SUCCESS"
        )
        assert "💾 [Retain]" in msg
        assert "Type: TASK" in msg
        assert "Outcome: UNKNOWN" in msg

    def test_retain_preserves_verified_task_success(self):
        import server
        msg = server.retain(
            content="Troubleshooting memory leak selesai. Fix confirmed via commit a1b2c3d, exit code 0, status 200 OK.",
            title="Fix Memory Leak Verified",
            bank_id="infra-sre",
            outcome_status="SUCCESS"
        )
        assert "💾 [Retain]" in msg
        assert "Type: TASK" in msg
        assert "Outcome: SUCCESS" in msg

    def test_failed_validation_zero_partial_graph_write(self):
        """Acceptance Test 11: Failed validation creates zero partial nodes in graph."""
        import server
        unique_secret = "-----BEGIN OPENSSH PRIVATE KEY-----\nsecret_token_1234567890\n-----END OPENSSH PRIVATE KEY-----"
        unique_title = "Zero Partial Write Test Marker"
        msg = server.retain(
            content=f"Payload dengan kredensial: {unique_secret}",
            title=unique_title,
            bank_id="infra-sre"
        )
        assert "🚫 [IngestionGate: QUARANTINED]" in msg
        # Pastikan tidak ada episode dengan title ini di graph
        with server.driver.session() as s:
            rec = s.run("MATCH (e:Episode {title: $t}) RETURN count(e) as c", t=unique_title).single()
            assert rec["c"] == 0

    def test_unresolvable_evidence_reference_downgraded_to_unknown(self, gate):
        """Acceptance Test 12: Vague claims like 'verified on staging' without anchors are unverified."""
        content = "Perbaikan modul payment telah diverifikasi di staging dan semuanya berhasil."
        res = gate.validate(
            content=content,
            title="Payment Module Verification",
            bank_id="general",
            record_type="TASK",
            outcome_status="SUCCESS"
        )
        assert res.valid is True
        assert res.outcome_status == CanonicalOutcomeStatus.UNKNOWN.value
        assert res.review_decision == "NEEDS_MORE_EVIDENCE"

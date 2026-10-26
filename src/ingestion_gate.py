"""
MemoriaGraph 3.2.0 - Shared Memory Ingestion Quality Gate
Reference: docs/research/MEMORIAGRAPH-MEMORY-INGESTION-QUALITY-STANDARD.md

Gerbang validasi, normalisasi, dan proteksi tunggal untuk SEMUA write path:
- MCP Tool: retain() & record_cognitive_episode()
- HTTP API: POST /retain (port 8085)
- Core: EpisodeManager & Harvester
- Bridge: record_log.py

Aturan Pokok:
1. Hard Guardrail Rahasia: Menghalau private key dan token mentah sebelum embedding/DB.
2. Anti-Slop: Pembersihan klise basa-basi AI pembuka dan penutup.
3. Canonical Record Type & Outcome Applicability Deterministic Mapping.
4. Fact Grounding: Menolak klaim SUCCESS tanpa bukti nyata (downgrade ke UNKNOWN).
5. Idempotency Fingerprint: Mencegah duplikasi node pada penulisan ulang.
"""

from dataclasses import dataclass, field
import datetime
from datetime import timezone
from enum import Enum
import hashlib
import json
import os
import re
from typing import Any

from src.sanitizer import SECRET_PATTERNS, sanitize_string
from src.semantic_sanitizer import (
    EMPIRICAL_ANCHORS,
    classify_epistemic_grounding,
    slugify_bank_id,
    strip_conversational_fluff,
)


class CanonicalRecordType(str, Enum):
    TASK = "TASK"
    INCIDENT = "INCIDENT"
    DECISION = "DECISION"
    CONSTRAINT = "CONSTRAINT"
    OBSERVATION = "OBSERVATION"
    PLAN = "PLAN"
    REFERENCE = "REFERENCE"


class CanonicalOutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OutcomeApplicability(str, Enum):
    YES = "YES"
    NO = "NO"


class ProvenanceType(str, Enum):
    OBSERVED = "OBSERVED"
    USER_REPORTED = "USER_REPORTED"
    INFERRED = "INFERRED"
    ARTIFACT_VERIFIED = "ARTIFACT_VERIFIED"


class IngestionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_SHADOW = "ACCEPTED_SHADOW"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


# Reason Codes untuk Auditability
REASON_OK = "VALIDATION_PASSED"
REASON_SECRET_DETECTED = "CRITICAL_SECRET_DETECTED"
REASON_TITLE_EMPTY = "TITLE_EMPTY_OR_INVALID"
REASON_CONTENT_EMPTY = "CONTENT_EMPTY"
REASON_FLUFF_STRIPPED = "CONVERSATIONAL_FLUFF_STRIPPED"
REASON_UNVERIFIED_SUCCESS_DOWNGRADED = "UNVERIFIED_SUCCESS_DOWNGRADED_TO_UNKNOWN"
REASON_UNVERIFIED_FAILURE_DOWNGRADED = "UNVERIFIED_FAILURE_DOWNGRADED_TO_UNKNOWN"
REASON_INTERMEDIATE_FAILURE_OVERRIDDEN = "INTERMEDIATE_FAILURE_OVERRIDDEN_BY_RECOVERY"
REASON_NON_TASK_OUTCOME_NEUTRALIZED = "NON_TASK_OUTCOME_SET_NOT_APPLICABLE"
REASON_EVIDENCE_ARTIFACT_VERIFIED = "EVIDENCE_ARTIFACT_VERIFIED"
REASON_INTERMEDIATE_FAILURE_PRESERVED = "INTERMEDIATE_FAILURE_PRESERVED"
REASON_NOISE_REJECTED = "LOW_VALUE_NOISE_REJECTED"
REASON_SHADOW_MODE_RECORDED = "SHADOW_MODE_RECORDED"


@dataclass
class IngestionValidationResult:
    valid: bool
    status: IngestionStatus
    record_type: str
    outcome_applicable: str
    outcome_status: str
    review_decision: str
    confidence_stage: str
    provenance: str
    fingerprint: str
    sanitized_title: str
    sanitized_content: str
    bank: str
    reason_codes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "status": self.status.value,
            "record_type": self.record_type,
            "outcome_applicable": self.outcome_applicable,
            "outcome_status": self.outcome_status,
            "review_decision": self.review_decision,
            "confidence_stage": self.confidence_stage,
            "provenance": self.provenance,
            "fingerprint": self.fingerprint,
            "sanitized_title": self.sanitized_title,
            "sanitized_content": self.sanitized_content,
            "bank": self.bank,
            "reason_codes": self.reason_codes,
            "errors": self.errors,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


def detect_critical_secrets(text: str) -> list[str]:
    """Mendeteksi apakah terdapat rahasia berisiko tinggi tanpa mengekspos isi rahasia."""
    detected = []
    # Bersihkan placeholder yang sudah diredaksi sebelumnya agar tidak menjadi false positive
    clean_text = re.sub(r"\[(REDACTED|QUARANTINED)_[A-Z0-9_]+\]", "", text)
    for pattern, name in SECRET_PATTERNS:
        if re.search(pattern, clean_text, flags=re.IGNORECASE):
            clean_name = name.strip("[]")
            if clean_name not in detected:
                detected.append(clean_name)
    return detected


POSITIVE_EVIDENCE_PATTERNS = [
    r"\bexit\s+code\s+0\b",
    r"\bstatus\s+(code\s+)?(200|201|204|ok|running|active)\b",
    r"\b\d+\s+passed(\s+in\s+[\d\.]+s)?\b",
    r"\b(lulus|passed|verified)\s+(uat|test|audit|benchmark)\b",
    r"\bcommit\s+[0-9a-f]{7,40}\b",
    r"\bhash\s*[:=]?\s*[0-9a-f]{7,40}\b",
    r"\b200\s+ok\b",
    r"\btests?:\s*\d+\s+passed\b",
]

FAILURE_EVIDENCE_PATTERNS = [
    r"\bexit\s+code\s+[1-9]\d*\b",
    r"\bstatus\s+(code\s+)?([45][0-9]{2}|error|failed|crashed|fatal)\b",
    r"\b(traceback|stacktrace|exception|segmentation fault|sigsegv|sigkill|oom|out of memory)\b",
    r"\b(failed|failure|gagal)\s+(uat|test|audit|benchmark|build|compile)\b",
    r"\b\d+\s+failed\b",
    r"\bcrashloopbackoff\b",
    r"\berror\s*:\s*.+",
]


def check_has_empirical_evidence(text: str, attempts: list | None = None) -> bool:
    """Memeriksa apakah terdapat bukti empiris keberhasilan nyata (commit hash, exit code 0, status 200, test report)."""
    # 1. Cek pola positif empiris pada teks
    has_pos = any(re.search(pat, text, flags=re.IGNORECASE) for pat in POSITIVE_EVIDENCE_PATTERNS)
    if has_pos:
        return True

    # 2. Cek attempts terstruktur
    if attempts:
        for att in attempts:
            if isinstance(att, dict):
                res = str(att.get("result", ""))
                act = str(att.get("action", ""))
                combined = f"{act} {res}"
                if any(re.search(pat, combined, flags=re.IGNORECASE) for pat in POSITIVE_EVIDENCE_PATTERNS):
                    return True
                if str(att.get("status", "")).upper() in ["SUCCESS", "RESOLVED"]:
                    if len(res.strip()) > 10 and not any(w in res.lower() for w in ["mungkin", "kayaknya", "diduga"]):
                        return True

    return False


def check_has_failure_evidence(text: str, attempts: list | None = None) -> bool:
    """Memeriksa apakah terdapat bukti kesalahan / kegagalan nyata (exit code non-zero, crash, traceback, OOM)."""
    # 1. Cek pola kegagalan pada teks
    has_fail = any(re.search(pat, text, flags=re.IGNORECASE) for pat in FAILURE_EVIDENCE_PATTERNS)
    if has_fail:
        return True

    # 2. Cek attempts terstruktur
    if attempts:
        for att in attempts:
            if isinstance(att, dict):
                res = str(att.get("result", ""))
                act = str(att.get("action", ""))
                combined = f"{act} {res}"
                if any(re.search(pat, combined, flags=re.IGNORECASE) for pat in FAILURE_EVIDENCE_PATTERNS):
                    return True
                if str(att.get("status", "")).upper() in ["FAILED", "FAILURE", "ERROR"]:
                    return True

    return False


def infer_record_type_from_context(
    title: str,
    content: str,
    explicit_category: str = "",
    explicit_type: str = ""
) -> CanonicalRecordType:
    """Menentukan record type canonical berdasarkan konten dan kategori."""
    if explicit_type and explicit_type.strip().upper() in CanonicalRecordType.__members__:
        return CanonicalRecordType(explicit_type.strip().upper())

    combined = f"{title} {content} {explicit_category}".lower()

    if any(k in combined for k in ["rencana", "roadmap", "agenda", "jadwal", "plan", "blueprint"]):
        return CanonicalRecordType.PLAN
    if any(k in combined for k in ["insiden", "incident", "outage", "downtime", "kebocoran", "breach", "crash"]):
        return CanonicalRecordType.INCIDENT
    if any(k in combined for k in ["keputusan", "memilih", "decision", "tradeoff", "trade-off", "opsi"]):
        return CanonicalRecordType.DECISION
    if any(k in combined for k in ["aturan", "constraint", "larangan", "limitasi", "kebijakan", "policy", "wajib"]):
        return CanonicalRecordType.CONSTRAINT
    if any(k in combined for k in ["observasi", "temuan", "monitoring", "pantauan", "observation", "patrol"]):
        return CanonicalRecordType.OBSERVATION
    if any(k in combined for k in ["referensi", "dokumentasi", "manual", "panduan", "docs", "reference", "catatan"]):
        return CanonicalRecordType.REFERENCE

    # Default untuk pengerjaan rekayasa software / bug fixing
    return CanonicalRecordType.TASK


def compute_idempotency_fingerprint(bank: str, record_type: str, title: str, content: str) -> str:
    """Menghitung SHA-256 fingerprint stabil untuk mencegah duplikasi episode."""
    norm_title = re.sub(r"\s+", " ", title.strip().lower())
    norm_content = re.sub(r"\s+", " ", content.strip().lower()[:300])
    raw = f"{bank.strip().lower()}:{record_type.strip().upper()}:{norm_title}:{norm_content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MemoryIngestionQualityGate:
    """
    Pilar Gerbang Kualitas Ingestion Terpadu (Memory Ingestion Quality Gate).
    Menjamin integritas data sebelum menyentuh vektor atau graph Neo4j.
    """

    def __init__(self, enforce: bool = True):
        # Membaca environment flag (default true)
        env_val = os.getenv("MEMORIAGRAPH_ENFORCE_INGESTION_GATE", "true").strip().lower()
        self.enforce = (env_val == "true") and enforce

    def validate(
        self,
        content: str,
        title: str = "",
        bank_id: str = "general",
        category: str = "PROBLEM_SOLVING",
        record_type: str = "",
        outcome_status: str = "UNKNOWN",
        attempts: list | str | None = None,
        source_reference: str = "manual",
        provenance: str = "OBSERVED"
    ) -> IngestionValidationResult:
        """
        Melakukan validasi murni dan normalisasi terhadap payload ingestion.
        """
        reasons = []
        errors = []

        # 1. Secret Detection (Hard Guardrail)
        secrets_detected = detect_critical_secrets(f"{title} {content}")
        if secrets_detected:
            reasons.append(REASON_SECRET_DETECTED)
            if self.enforce:
                errors.append(f"Payload ditolak: Terdeteksi kredensial sensitif: {', '.join(secrets_detected)}.")
                return IngestionValidationResult(
                    valid=False,
                    status=IngestionStatus.QUARANTINED,
                    record_type=record_type or "UNKNOWN",
                    outcome_applicable="NO",
                    outcome_status="REJECTED_SECRET",
                    review_decision="QUARANTINED",
                    confidence_stage="HYPOTHESIS",
                    provenance="USER_REPORTED",
                    fingerprint="",
                    sanitized_title="[QUARANTINED]",
                    sanitized_content="[QUARANTINED_SECRET_PAYLOAD]",
                    bank=slugify_bank_id(bank_id),
                    reason_codes=reasons,
                    errors=errors,
                    metadata={"secrets_detected": secrets_detected}
                )
            else:
                reasons.append(REASON_SHADOW_MODE_RECORDED)
                content = sanitize_string(content)
                title = sanitize_string(title)

        # 2. Pembersihan Fluff & Conversational Slop
        clean_content = strip_conversational_fluff(content)
        if len(clean_content) < len(content.strip()):
            reasons.append(REASON_FLUFF_STRIPPED)

        # Sanitasi teks (redaksi nilai rahasia minor bila ada)
        clean_content = sanitize_string(clean_content)

        # Evaluasi kegunaan & validitas minimum
        if not clean_content or len(clean_content.strip()) < 5:
            if self.enforce:
                errors.append("Konten memori kosong atau terlalu pendek (kurang dari 5 karakter).")
                return IngestionValidationResult(
                    valid=False,
                    status=IngestionStatus.REJECTED,
                    record_type=record_type or "UNKNOWN",
                    outcome_applicable="NO",
                    outcome_status="REJECTED_EMPTY",
                    review_decision="NOT_APPLICABLE",
                    confidence_stage="HYPOTHESIS",
                    provenance=provenance,
                    fingerprint="",
                    sanitized_title=title,
                    sanitized_content="",
                    bank=slugify_bank_id(bank_id),
                    reason_codes=[REASON_CONTENT_EMPTY],
                    errors=errors
                )
            else:
                reasons.append(REASON_CONTENT_EMPTY)
                reasons.append(REASON_SHADOW_MODE_RECORDED)

        # 3. Normalisasi Judul
        clean_title = sanitize_string(strip_conversational_fluff(title))
        if not clean_title:
            first_line = clean_content.split("\n")[0].strip()
            clean_title = (first_line[:60] + "...") if len(first_line) > 60 else first_line
            if not clean_title:
                clean_title = f"Memori {category.title()} ({bank_id})"

        bank = slugify_bank_id(bank_id)

        # 4. Canonical Record Type Assignment
        rec_type = infer_record_type_from_context(
            title=clean_title,
            content=clean_content,
            explicit_category=category,
            explicit_type=record_type
        )

        # 5. Parsing Attempts jika ada
        parsed_attempts = []
        if attempts:
            if isinstance(attempts, str):
                try:
                    parsed_attempts = json.loads(attempts)
                except Exception:
                    parsed_attempts = [{"action": attempts, "status": "UNKNOWN"}]
            elif isinstance(attempts, list):
                parsed_attempts = attempts

        # 6. Outcome & Applicability Validation (Fact Grounding)
        raw_status = (outcome_status or "UNKNOWN").strip().upper()
        if raw_status in ["AUTO", "DEFAULT", ""]:
            raw_status = "UNKNOWN"

        has_positive_evidence = check_has_empirical_evidence(clean_content, parsed_attempts)
        has_failure_evidence = check_has_failure_evidence(clean_content, parsed_attempts)

        # Deteksi apakah attempt berurutan menunjukkan recovery (intermediate failure -> success)
        has_recovered_attempt = False
        if parsed_attempts:
            had_failure = any(str(a.get("status", "")).upper() in ["FAILED", "FAILURE", "ERROR"] for a in parsed_attempts if isinstance(a, dict))
            last_attempt = parsed_attempts[-1] if isinstance(parsed_attempts[-1], dict) else {}
            last_is_success = str(last_attempt.get("status", "")).upper() in ["SUCCESS", "RESOLVED"]
            if had_failure and last_is_success:
                has_recovered_attempt = True

        if rec_type in [CanonicalRecordType.TASK, CanonicalRecordType.INCIDENT]:
            out_applicable = OutcomeApplicability.YES.value
            if raw_status in ["SUCCESS", "RESOLVED"]:
                if has_positive_evidence:
                    final_outcome = CanonicalOutcomeStatus.SUCCESS.value
                    review_dec = "SUCCESS"
                    reasons.append(REASON_EVIDENCE_ARTIFACT_VERIFIED)
                else:
                    # Downgrade: Task/Incident tanpa bukti empiris dilarang berstatus SUCCESS!
                    final_outcome = CanonicalOutcomeStatus.UNKNOWN.value
                    review_dec = "NEEDS_MORE_EVIDENCE"
                    reasons.append(REASON_UNVERIFIED_SUCCESS_DOWNGRADED)
            elif raw_status in ["PARTIAL", "PARTIAL_SUCCESS"]:
                final_outcome = CanonicalOutcomeStatus.PARTIAL.value
                review_dec = "PARTIAL"
            elif raw_status in ["FAILURE", "FAILED"]:
                if has_recovered_attempt:
                    final_outcome = CanonicalOutcomeStatus.SUCCESS.value if has_positive_evidence else CanonicalOutcomeStatus.PARTIAL.value
                    review_dec = "SUCCESS" if has_positive_evidence else "PARTIAL"
                    reasons.append(REASON_INTERMEDIATE_FAILURE_OVERRIDDEN)
                elif has_failure_evidence:
                    final_outcome = CanonicalOutcomeStatus.FAILURE.value
                    review_dec = "FAILURE"
                else:
                    final_outcome = CanonicalOutcomeStatus.UNKNOWN.value
                    review_dec = "NEEDS_MORE_EVIDENCE"
                    reasons.append(REASON_UNVERIFIED_FAILURE_DOWNGRADED)
            else:
                final_outcome = CanonicalOutcomeStatus.UNKNOWN.value
                review_dec = "NEEDS_MORE_EVIDENCE"
        else:
            # Non-Task (PLAN, DECISION, CONSTRAINT, OBSERVATION, REFERENCE)
            out_applicable = OutcomeApplicability.NO.value
            final_outcome = CanonicalOutcomeStatus.NOT_APPLICABLE.value
            review_dec = "NOT_APPLICABLE"
            reasons.append(REASON_NON_TASK_OUTCOME_NEUTRALIZED)

        # 7. Epistemic Grounding (Fact vs Inference vs Hypothesis)
        epistemic_res = classify_epistemic_grounding(f"{clean_title} {clean_content}")
        if isinstance(epistemic_res, tuple):
            confidence_stage = epistemic_res[0]
            epistemic_score = epistemic_res[1]
        else:
            confidence_stage = str(epistemic_res)
            epistemic_score = 0.5

        # 8. Provenance
        if has_positive_evidence:
            provenance_final = ProvenanceType.ARTIFACT_VERIFIED.value
        elif provenance and provenance.upper() in ProvenanceType.__members__:
            provenance_final = provenance.upper()
        else:
            provenance_final = ProvenanceType.OBSERVED.value

        # 9. Idempotency Fingerprint
        fingerprint = compute_idempotency_fingerprint(bank, rec_type.value, clean_title, clean_content)

        if not self.enforce:
            final_status = IngestionStatus.ACCEPTED_SHADOW
            if REASON_SHADOW_MODE_RECORDED not in reasons:
                reasons.append(REASON_SHADOW_MODE_RECORDED)
        else:
            final_status = IngestionStatus.ACCEPTED
            reasons.append(REASON_OK)

        return IngestionValidationResult(
            valid=True,
            status=final_status,
            record_type=rec_type.value,
            outcome_applicable=out_applicable,
            outcome_status=final_outcome,
            review_decision=review_dec,
            confidence_stage=confidence_stage,
            provenance=provenance_final,
            fingerprint=fingerprint,
            sanitized_title=clean_title,
            sanitized_content=clean_content,
            bank=bank,
            reason_codes=reasons,
            errors=[],
            metadata={
                "has_empirical_evidence": has_positive_evidence,
                "has_failure_evidence": has_failure_evidence,
                "has_recovered_attempt": has_recovered_attempt,
                "parsed_attempts_count": len(parsed_attempts),
                "source_reference": source_reference
            }
        )


# Global Singleton Gate
ingestion_gate = MemoryIngestionQualityGate()

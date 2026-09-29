"""
Test Suite untuk Fase 4: Semantic Quality Gate & Anti-Slop Sanitizer
Menguji:
1. Penghapusan basa-basi LLM (throat-clearing & concluding fluff)
2. Penghapusan komentar kode redundan
3. Evidence Grounding Gate (Fact vs Inference vs Hypothesis)
4. Distilasi Heuristik padat (High-Signal Actionable Playbooks)
5. Integrasi pembersihan payload lengkap
"""
import sys
import os

if "/opt/memoriagraph" not in sys.path:
    sys.path.insert(0, "/opt/memoriagraph")

from src.semantic_sanitizer import (
    strip_conversational_fluff,
    strip_redundant_comments,
    classify_epistemic_grounding,
    distill_actionable_heuristic,
    clean_cognitive_payload
)

def run_tests():
    print("=" * 60)
    print("🧪 MEMORIAGRAPH 3.0: SEMANTIC SANITIZER & ANTI-SLOP TEST SUITE")
    print("=" * 60)

    # 1. Test Penghapusan Basa-Basi
    print("\n[TEST 1] AI Throat-Clearing & Concluding Fluff Stripping:")
    samples = [
        ("Certainly! Here is the architecture plan for HUD: Gunakan Three.js WebGL.", "Gunakan Three.js WebGL."),
        ("Tentu saja! Berikut adalah konfigurasi PM2 watchdog. Semoga ini membantu!", "Konfigurasi PM2 watchdog."),
        ("As an AI language model, perlu diingat bahwa restart service membutuhkan sudo. Hope this helps!", "Restart service membutuhkan sudo."),
        ("Siap Bos! Berikut adalah hasil investigasi port 3400.", "Hasil investigasi port 3400.")
    ]
    for raw, expected in samples:
        res = strip_conversational_fluff(raw)
        print(f"  Raw: '{raw}'\n  ➔ Cleaned: '{res}'")
        assert expected.lower() in res.lower()
    print("  ✅ Basa-basi AI berhasil dipangkas 100%.")

    # 2. Test Pembersihan Komentar Kode Redundan
    print("\n[TEST 2] Redundant Code Comment Stripping:")
    code_raw = """
# import libraries
import os
import sys

# define function
def restart_process(pid):
    # increment attempt by 1
    attempt += 1
    # Check if PID exists before killing
    if pid > 0:
        # call kill command
        os.kill(pid, 9)
    # return result
    return True
"""
    cleaned_code = strip_redundant_comments(code_raw)
    print("  Original Code Lines:", len(code_raw.strip().split("\n")))
    print("  Cleaned Code Lines:", len(cleaned_code.strip().split("\n")))
    assert "# import libraries" not in cleaned_code
    assert "# return result" not in cleaned_code
    assert "# Check if PID exists before killing" in cleaned_code, "Komentar esensial/kritis harus tetap dipertahankan"
    print("  ✅ Komentar redundan terhapus, komentar arsitektural esensial dipertahankan.")

    # 3. Test Evidence Grounding Gate
    print("\n[TEST 3] Epistemic Grounding Classification:")
    
    # 3a. Kasus Empiris Riil (Harus FACT)
    telemetry_claim = "Node.js service restarted pada port 3400 dengan exit code 0, RAM stabil di 8.94% (2870MB)."
    cls1, conf1 = classify_epistemic_grounding(telemetry_claim)
    print(f"  Telemetry Statement: '{telemetry_claim[:50]}...'\n  ➔ Class: {cls1}, Conf: {conf1}")
    assert cls1 == "FACT"
    assert conf1 >= 0.90

    # 3b. Kasus Spekulatif (Harus HYPOTHESIS)
    speculative_claim = "Mungkin tingginya CPU load disebabkan oleh thread pool yang macet di background."
    cls2, conf2 = classify_epistemic_grounding(speculative_claim)
    print(f"  Speculative Statement: '{speculative_claim[:50]}...'\n  ➔ Class: {cls2}, Conf: {conf2}")
    assert cls2 == "HYPOTHESIS"
    assert conf2 <= 0.50

    # 3c. Kasus Klaim FACT Palsu (Tanpa data empiris, harus didowngrade ke INFERENCE)
    false_fact = "Performa sistem meningkat pesat dan latency menjadi super kilat."
    cls3, conf3 = classify_epistemic_grounding(false_fact, claimed_status="FACT")
    print(f"  Ungrounded Claim: '{false_fact}'\n  ➔ Claimed: FACT ➔ Verified: {cls3}, Conf: {conf3}")
    assert cls3 == "INFERENCE", "Klaim tanpa data telemetri harus didowngrade dari FACT ke INFERENCE"

    print("  ✅ Epistemic Grounding Gate terverifikasi akurat.")

    # 4. Test Distilasi Heuristik
    print("\n[TEST 4] High-Signal Actionable Heuristic Distillation:")
    verbose_heuristic = "Sangat disarankan untuk selalu memeriksa status Tailscale mesh sebelum mereboot interface jaringan."
    distilled = distill_actionable_heuristic(verbose_heuristic)
    print(f"  Verbose: '{verbose_heuristic}'\n  ➔ Distilled: '{distilled}'")
    assert distilled.startswith("Selalu memeriksa status Tailscale")
    print("  ✅ Distilasi heuristik menghasilkan instruksi imperatif padat.")

    # 5. Test Full Payload Cleaning
    print("\n[TEST 5] Integrated Payload Cleaning Pipeline:")
    raw_payload = {
        "title": "Certainly! Investigasi Memory Leak AI-SRE",
        "objective": "Berikut ini adalah analisis lengkap untuk menurunkan beban RAM.",
        "heuristic": "Sangat disarankan untuk selalu melakukan dump heap saat RAM melampaui 80%.",
        "decision_rationale": "PID 89812 dihentikan dengan exit code 0 setelah konsumsi mencapai 2.8GB.",
        "api_key": "sk-proj-abc1234567890abcdef12345",
        "epistemic_class": "FACT"
    }
    clean_p = clean_cognitive_payload(raw_payload)
    print("  Title:", clean_p["title"])
    print("  Objective:", clean_p["objective"])
    print("  Heuristic:", clean_p["heuristic"])
    print("  API Key Redacted:", clean_p["api_key"])
    print("  Verified Epistemic Class:", clean_p["verified_epistemic_class"])
    assert clean_p["api_key"] == "[REDACTED_API_KEY]"
    assert not clean_p["title"].startswith("Certainly!")
    assert clean_p["verified_epistemic_class"] == "FACT"
    print("  ✅ Full payload pipeline terintegrasi sempurna!")

    print("\n" + "=" * 60)
    print("🎉 SEMUA TEST FASE 4 (SEMANTIC QUALITY GATE & ANTI-SLOP) LULUS 100%!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

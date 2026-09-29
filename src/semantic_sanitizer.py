"""
MemoriaGraph 3.0 - Semantic Quality Gate & Anti-Slop Sanitizer (Anti-Slop Pillar)
Mencegah memori kognitif tercemar oleh:
1. Klise / basa-basi percakapan LLM (AI throat-clearing & concluding fluff).
2. Tautologi & ringkasan melingkar (circular summaries).
3. Klaim tanpa bukti empiris (Evidence Grounding Gate: Fact vs Inference vs Hypothesis).
4. Komentar redundan pada cuplikan kode.
"""

import re
from typing import Any

from src.sanitizer import sanitize_data

# Pola pembuka klise AI (throat-clearing)
AI_PREFACE_PATTERNS = [
    r"^(certainly!|sure!|of course!|sure thing!|as requested,?)\s*",
    r"^(tentu saja!|tentu!|siap bos!|dengan senang hati!|berikut adalah|berikut ini)\s*[\:\,\.]?\s*",
    r"^(here is|here are|below is|the following is|in this section,?)\s*[\:\,\.]?\s*",
    r"^(sebagai model ai|as an ai language model|as an assistant),?\s*",
    r"^(perlu dicatat bahwa|perlu diingat bahwa|harap perhatikan bahwa),?\s*",
    r"^(it is important to note that|please note that|keep in mind that),?\s*",
]

# Pola penutup klise AI (concluding fluff)
AI_CLOSING_PATTERNS = [
    r"\s*(semoga ini membantu!?|semoga bermanfaat!?|semoga berhasil!?)$",
    r"\s*(hope this helps!?|hope that helps!?|let me know if you need anything else!?)$",
    r"\s*(feel free to ask if you have any questions!?)$",
    r"\s*(jika ada pertanyaan lebih lanjut,? jangan ragu untuk bertanya\.?)$",
    r"\s*(kesimpulannya,?.+sehingga.+bermanfaat\.?)$",
]

# Komentar kode yang sangat sepele / redundan
OBVIOUS_CODE_COMMENTS = [
    r"^\s*#\s*(import\s+.*|define\s+.*|call\s+.*|set\s+.*|return\s+.*|end\s+.*|init\s+.*|start\s+.*|setup\s+.*)$",
    r"^\s*//\s*(import\s+.*|define\s+.*|call\s+.*|set\s+.*|return\s+.*|end\s+.*|init\s+.*|start\s+.*|setup\s+.*)$",
    r"^\s*#\s*(increment\s+.*|loop\s+.*|check\s+condition)$",
    r"^\s*//\s*(increment\s+.*|loop\s+.*|check\s+condition)$",
]

# Indikator bukti empiris (Evidence Grounding)
EMPIRICAL_ANCHORS = [
    r"\bexit\s+code\s+\d+\b",
    r"\bcode\s+[0-9]+\b",
    r"\bstatus\s+[2-5][0-9]{2}\b",
    r"\b\d+(\.\d+)?\s*(%|mb|gb|tb|ms|s|sec|seconds|kbps|mbps|ghz|mhz|cores|threads)\b",
    r"\b(pm2|docker|container|systemd|tailscale|kvm|qemu)\b",
    r"\b(pid\s+\d+|port\s+\d+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\b",
    r"\b[0-9a-f]{7,40}\b", # Git hash
    r"/(bin|usr|opt|etc|home|root|var|sys|proc)/[a-zA-Z0-9_\-\./]+", # Unix path
]

# Kata-kata indikator spekulasi / hipotesis
SPECULATIVE_WORDS = [
    r"\b(mungkin|kemungkinan|sepertinya|diduga|bisa jadi|barangkali)\b",
    r"\b(presumably|hypothetically|apparently|might be|could be|speculate|perhaps)\b",
    r"\b(belum diverifikasi|unverified|asumsi|assumption)\b",
]

def strip_conversational_fluff(text: str) -> str:
    """Membersihkan basa-basi pembuka dan penutup khas respons LLM."""
    if not isinstance(text, str):
        return text
        
    cleaned = text.strip()
    
    # Bersihkan pembuka
    for pattern in AI_PREFACE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        
    # Bersihkan penutup
    for pattern in AI_CLOSING_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        
    # Perbaiki huruf kapital awal kalimat jika terpotong
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
        
    return cleaned

def strip_redundant_comments(code_snippet: str) -> str:
    """Menghapus komentar kode redundan yang tidak memberi nilai tambah arsitektur."""
    if not isinstance(code_snippet, str):
        return code_snippet
        
    lines = code_snippet.split("\n")
    filtered_lines = []
    
    for line in lines:
        is_redundant = False
        for pat in OBVIOUS_CODE_COMMENTS:
            if re.match(pat, line, flags=re.IGNORECASE):
                is_redundant = True
                break
        if not is_redundant:
            filtered_lines.append(line)
            
    return "\n".join(filtered_lines)

def classify_epistemic_grounding(statement: str, claimed_status: str | None = None) -> tuple[str, float]:
    """
    Quality Gate Epistemologis:
    Memverifikasi apakah suatu klaim adalah FACT (didukung data empiris riil),
    INFERENCE (penalaran logis tanpa metrik riil), atau HYPOTHESIS (dugaan spekulatif).
    Mengembalikan (label_epistemik, skor_kepercayaan_awal).
    """
    if not isinstance(statement, str) or not statement.strip():
        return "UNKNOWN", 0.0
        
    text_lower = statement.lower()
    
    # 1. Cek keberadaan indikator spekulasi
    speculative_hits = sum(1 for pat in SPECULATIVE_WORDS if re.search(pat, text_lower))
    
    # 2. Cek keberadaan bukti empiris riil
    empirical_hits = sum(1 for pat in EMPIRICAL_ANCHORS if re.search(pat, text_lower))
    
    # Logika Epistemik Anti-Slop
    if speculative_hits > 0 and empirical_hits == 0:
        return "HYPOTHESIS", 0.40
        
    if empirical_hits >= 1 and speculative_hits == 0:
        return "FACT", 0.95
        
    if claimed_status and claimed_status.upper() in ["FACT", "OBSERVATION"] and empirical_hits == 0:
        # Klaim mengaku FACT tapi tidak menyertakan bukti telemetri/log nyata -> downgrade ke INFERENCE
        return "INFERENCE", 0.60
        
    if claimed_status and claimed_status.upper() in ["HYPOTHESIS", "SPECULATION"]:
        return "HYPOTHESIS", 0.45
        
    return "INFERENCE", 0.65

def distill_actionable_heuristic(heuristic_text: str) -> str:
    """
    Memadatkan heuristik menjadi playbook ringkas & berkeputusan tinggi (High-Signal).
    Membuang kalimat pengantar melingkar.
    """
    if not isinstance(heuristic_text, str):
        return heuristic_text
        
    cleaned = strip_conversational_fluff(heuristic_text)
    
    # Hapus frase melingkar seperti "Sangat disarankan untuk selalu..."
    cleaned = re.sub(r"^(sangat disarankan untuk\s*(selalu)?|disarankan agar\s*(selalu)?|selalu pastikan untuk|it is recommended to(\s+always)?)\s*", "Selalu ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(hindari melakukan|jangan pernah melakukan)\s*", "Hindari ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(gunakanlah|manfaatkan)\s*", "Gunakan ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(selalu\s+)+", "Selalu ", cleaned, flags=re.IGNORECASE)
    
    # Hapus jeda ganda dan perbaiki spasi
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def clean_cognitive_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Pipeline Lengkap Semantic Quality Gate:
    1. Redaksi kredensial rahasia (sanitizer.py).
    2. Pembersihan basa-basi LLM (throat-clearing).
    3. Distilasi heuristik menjadi aksi padat.
    4. Evaluasi grounding epistemik.
    """
    # 1. Sanitasi secret
    sanitized = sanitize_data(data)
    
    # 2. Pembersihan semantik pada field teks
    text_fields = ["title", "objective", "problem_description", "decision_choice", "decision_rationale", "reflection_lesson", "heuristic"]
    for field in text_fields:
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = strip_conversational_fluff(sanitized[field])
            
    # 3. Distilasi khusus heuristik
    if sanitized.get("heuristic"):
        sanitized["heuristic"] = distill_actionable_heuristic(sanitized["heuristic"])
        
    if sanitized.get("reflection_lesson"):
        sanitized["reflection_lesson"] = strip_conversational_fluff(sanitized["reflection_lesson"])
        
    # 4. Validasi kelas epistemik
    candidate_text = sanitized.get("problem_description", "") + " " + sanitized.get("decision_rationale", "") + " " + sanitized.get("heuristic", "")
    epistemic_class, conf = classify_epistemic_grounding(candidate_text, claimed_status=sanitized.get("epistemic_class"))
    sanitized["verified_epistemic_class"] = epistemic_class
    sanitized["initial_epistemic_confidence"] = conf
    
    return sanitized

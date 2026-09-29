"""
MemoriaGraph 2.0 - Secret Sanitizer Engine
Melindungi graph memory dari kebocoran token, private key, dan kredensial rahasia.
"""
import re
from typing import Any, Dict, List, Union

SECRET_PATTERNS = [
    # Private Keys (PEM / OpenSSH)
    (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    (r"-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]+?-----END OPENSSH PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    
    # Generic API Keys & Tokens
    (r"(sk_live_[a-zA-Z0-9]{16,})", "[REDACTED_API_KEY]"),
    (r"(sk-proj-[a-zA-Z0-9_\-]{20,})", "[REDACTED_API_KEY]"),
    (r"(sk-ant-[a-zA-Z0-9_\-]{20,})", "[REDACTED_API_KEY]"),
    (r"(ghp_[a-zA-Z0-9]{36,})", "[REDACTED_GITHUB_TOKEN]"),
    (r"(gho_[a-zA-Z0-9]{36,})", "[REDACTED_GITHUB_TOKEN]"),
    (r"(glpat-[a-zA-Z0-9\-_]{20,})", "[REDACTED_GITLAB_TOKEN]"),
    (r"(AIza[0-9A-Za-z-_]{35})", "[REDACTED_GOOGLE_API_KEY]"),
    
    # Authorization Headers
    (r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[REDACTED_BEARER_TOKEN]"),
    
    # Passwords & Secrets in assignments
    (r"(password[\"']?\s*[:=]\s*[\"']?)([^\"'\s]{4,})([\"']?)", r"\1[REDACTED_PASSWORD]\3"),
    (r"(secret[\"']?\s*[:=]\s*[\"']?)([^\"'\s]{4,})([\"']?)", r"\1[REDACTED_SECRET]\3"),
    (r"(token[\"']?\s*[:=]\s*[\"']?)([^\"'\s]{10,})([\"']?)", r"\1[REDACTED_TOKEN]\3"),
]

def sanitize_string(text: str) -> str:
    """Membersihkan string dari kredensial sensitif."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern, repl in SECRET_PATTERNS:
        sanitized = re.sub(pattern, repl, sanitized, flags=re.IGNORECASE)
    return sanitized

def sanitize_data(data: Any) -> Any:
    """Secara rekursif membersihkan dict, list, atau string dari rahasia."""
    if isinstance(data, str):
        return sanitize_string(data)
    elif isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data

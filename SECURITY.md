# Security Policy

## 🔒 Zero-Trust & Secret Protection Guarantees

MemoriaGraph is designed as a persistent cognitive memory substrate for autonomous AI agents and SRE controllers. Because agents frequently inspect environment variables, command outputs, and private repositories, MemoriaGraph enforces a strict **Pre-Ingestion Secret Sanitization Policy**.

### Core Guarantees:
1. **Deterministic Redaction**:
   - Private Keys (RSA, Ed25519, EC, OpenSSH): `-----BEGIN [A-Z ]+ PRIVATE KEY-----` $\to$ `[REDACTED_PRIVATE_KEY]`
   - API Keys & Bearer Tokens (AWS, OpenAI, Gemini Studio, Anthropic, GitHub): `sk-[a-zA-Z0-9]{20,}` $\to$ `[REDACTED_API_KEY]`
   - Connection Strings: `bolt://...` or `postgres://user:password@...` masks credentials automatically.
   - High-Entropy Strings: Tokens with Shannon entropy $> 4.2$ are automatically quarantined.

2. **Network & Storage Isolation**:
   - By default, Neo4j runs in a container bound to localhost (`127.0.0.1:7687`), or optionally restricted to a private VPN/Tailscale WireGuard mesh IP (e.g. `100.x.y.z`) for secure multi-node architectures.
   - The graph database should NEVER be exposed to public `0.0.0.0` interfaces.
   - All backups and event stream logs are sanitized prior to disk storage.

3. **Semantic Anti-Slop Immune System**:
   - MemoriaGraph includes an active `SemanticSanitizer` preventing hallucinated metrics, unverified exit codes, and circular AI fluff from entering the long-term cognitive substrate.

4. **Zero-Default-Credential Policy & Entropy Generation**:
   - Starting with v3.2.0, MemoriaGraph strictly eliminates unauthenticated or default-password database states (`memoriagraph_pass`).
   - The universal installer mandates user-defined credentials or generates 16-character cryptographically secure passwords (`secrets.choice`), persisting them strictly in local `.env` and host MCP configs (ignored by `.gitignore` and `.dockerignore`).

5. **Adaptive Network Security Gateway**:
   - The HTTP microservice (`http_service.py`) incorporates `AdaptiveSecurityMiddleware` (`SECURITY_NETWORK_MODE`: `private`, `tailscale`, `all`), blocking public unauthorized traffic while allowing Docker bridge (`172.16.0.0/12`) and Tailscale mesh peers.

---

## 🛡️ Supported Versions

| Version | Supported          | Security Patches |
| ------- | ------------------ | ---------------- |
| 3.2.x   | :white_check_mark: | Active           |
| 3.1.x   | :white_check_mark: | Maintained       |
| 3.0.x   | :x:                | Deprecated       |
| 2.0.x   | :x:                | Unsupported      |
| 1.0.x   | :x:                | Unsupported      |

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability or credential leakage vector within MemoriaGraph:
1. **DO NOT** open a public issue.
2. Send a report privately via GitHub Security Advisories or contact `security@memoriagraph.org`.
3. Include details of the vulnerability, proof of concept, and affected version.
4. We aim to acknowledge receipt within 24 hours and patch critical issues within 48 hours.

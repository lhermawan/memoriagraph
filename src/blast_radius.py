"""
MemoriaGraph 3.0 - Git Blast-Radius Mapping (Codebase-Memory Pillar)
Menganalisis dampak perubahan kode/skrip secara otomatis dari git diff/status
dan memproyeksikannya ke node :Action di graph kognitif.
"""

import os
import sys
import subprocess
import datetime
import uuid
from typing import Dict, Any, List, Optional
import dotenv
from neo4j import GraphDatabase

dotenv.load_dotenv("/opt/memoriagraph/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "maskiisecret")

def analyze_git_blast_radius(repo_path: str = "/home/maskii/Private-key", base_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Menginspeksi git diff dan uncommitted changes di direktori target.
    Mengembalikan ringkasan file terdampak, blast radius severity, dan modul terkait.
    """
    if not os.path.exists(repo_path):
        return {"ok": False, "error": f"Path '{repo_path}' tidak ditemukan."}

    modified_files = []
    is_git_repo = os.path.exists(os.path.join(repo_path, ".git"))

    if is_git_repo:
        try:
            head_commit = subprocess.check_output(
                ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except Exception:
            head_commit = "untracked"

        try:
            status_raw = subprocess.check_output(
                ["git", "-C", repo_path, "status", "--porcelain"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            
            if status_raw:
                for line in status_raw.split("\n"):
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        modified_files.append(parts[1])

            if base_ref:
                diff_raw = subprocess.check_output(
                    ["git", "-C", repo_path, "diff", "--name-only", base_ref],
                    stderr=subprocess.DEVNULL,
                    text=True
                ).strip()
                if diff_raw:
                    for f in diff_raw.split("\n"):
                        if f and f not in modified_files:
                            modified_files.append(f)
        except Exception as e:
            return {"ok": False, "error": f"Gagal membaca git status: {e}"}
    else:
        # Fallback untuk non-git directory: pantau file termutakhir (< 24 jam)
        head_commit = "non-git-dir"
        now_ts = datetime.datetime.now().timestamp()
        for root, _, files in os.walk(repo_path):
            for file in files:
                fpath = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(fpath)
                    if (now_ts - mtime) < 86400: # 24 jam terakhir
                        rel = os.path.relpath(fpath, repo_path)
                        modified_files.append(rel)
                except Exception:
                    pass

    # 3. Analisis Area dan Severity
    affected_areas = set()
    has_config = False
    has_core_code = False

    for f in modified_files:
        f_lower = f.lower()
        if "hud" in f_lower:
            affected_areas.add("friday-hologram-hud")
        if "sre" in f_lower or "patrol" in f_lower:
            affected_areas.add("ai-sre-infrastructure")
        if "memoriagraph" in f_lower or "neo4j" in f_lower:
            affected_areas.add("memoriagraph-core")
        if f_lower.endswith((".env", ".json", ".yml", ".yaml", ".toml")):
            has_config = True
            affected_areas.add("configuration")
        if f_lower.endswith((".py", ".js", ".ts", ".go", ".sh")):
            has_core_code = True
            affected_areas.add("codebase-logic")
        if f_lower.endswith((".md", ".txt")):
            affected_areas.add("documentation")

    if not affected_areas:
        affected_areas.add("clean-workspace")

    # Hitung severity
    count = len(modified_files)
    if count == 0:
        severity = "CLEAN"
        risk = "Tidak ada perubahan file aktif."
    elif has_config or count >= 6:
        severity = "HIGH"
        risk = "Perubahan melibatkan file konfigurasi atau modul krusial multi-file."
    elif has_core_code or count >= 3:
        severity = "MEDIUM"
        risk = "Perubahan logika kode aktif. Uji coba fungsional direkomendasikan."
    else:
        severity = "LOW"
        risk = "Perubahan dokumentasi atau skrip minor."

    return {
        "ok": True,
        "repo_path": repo_path,
        "head_commit": head_commit,
        "total_files_changed": count,
        "modified_files": modified_files[:20],
        "affected_areas": list(affected_areas),
        "blast_severity": severity,
        "risk_assessment": risk,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def record_code_action_with_blast_radius(
    episode_id: str,
    action_description: str,
    repo_path: str = "/home/maskii/Private-key",
    base_ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mencatat node :Action di Neo4j lengkap dengan metadata Blast-Radius Git.
    """
    analysis = analyze_git_blast_radius(repo_path, base_ref=base_ref)
    act_id = f"ACT-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        cypher = """
        MATCH (e:Episode {id: $ep_id})
        CREATE (a:Action {
            id: $act_id,
            description: $desc,
            git_commit: $commit,
            files_changed_count: $files_count,
            blast_severity: $severity,
            affected_areas: $areas,
            timestamp: datetime($now)
        })
        MERGE (e)-[:EXECUTED_ACTION]->(a)
        RETURN a.id AS action_id
        """
        s.run(
            cypher,
            ep_id=episode_id,
            act_id=act_id,
            desc=action_description,
            commit=analysis.get("head_commit", "unknown"),
            files_count=analysis.get("total_files_changed", 0),
            severity=analysis.get("blast_severity", "LOW"),
            areas=analysis.get("affected_areas", []),
            now=now_iso
        )
    driver.close()

    return {
        "action_id": act_id,
        "episode_id": episode_id,
        "blast_radius": analysis
    }

if __name__ == "__main__":
    res = analyze_git_blast_radius("/home/maskii/Private-key")
    print("Blast Radius Analysis:", res)

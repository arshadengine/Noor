"""
brain/tools/filesystem.py
─────────────────────────────────────────────────────
Multi-Factor File Finder, Search Policy Engine & File Visibility Layer.
Metadata fields: visibility (user/system), searchable (bool), source, owner, priority.
Filters out internal Noor runtime artifacts (temp_audio, logs, cache, __pycache__, noor.db)
unless Developer Mode is active.
"""

import os
import re
from pathlib import Path
from datetime import datetime
from brain.db import get_db
from brain.system.workspace import is_developer_mode_active

SYSTEM_BLACK_PATHS = [
    r"data\temp_audio", r"data/temp_audio",
    r"\logs", r"/logs",
    r"\cache", r"/cache",
    r"__pycache__", r"\venv", r"/.venv",
    r"\.git", r"node_modules",
    "noor.db", ".tmp", "response_"
]


def classify_file_metadata(filepath: str, filename: str) -> dict:
    """Classify file metadata tags: visibility, searchable, source, owner, priority."""
    fp_lower = filepath.lower()
    fn_lower = filename.lower()

    # System / Internal Noor Runtime Artifacts
    if any(sp in fp_lower for sp in SYSTEM_BLACK_PATHS) or fn_lower == "noor.db":
        return {
            "visibility": "system",
            "searchable": False,
            "source": "system_runtime",
            "owner": "noor",
            "priority": 10
        }

    user_home = str(Path.home()).lower()
    source = "workspace"
    if rf"{user_home}\downloads" in fp_lower or rf"{user_home}/downloads" in fp_lower:
        source = "downloads"
    elif rf"{user_home}\documents" in fp_lower or rf"{user_home}/documents" in fp_lower:
        source = "documents"
    elif rf"{user_home}\desktop" in fp_lower or rf"{user_home}/desktop" in fp_lower:
        source = "desktop"

    return {
        "visibility": "user",
        "searchable": True,
        "source": source,
        "owner": "user",
        "priority": 90 if source == "workspace" else 80
    }


def find_and_rank_files(query: str, active_workspace: str = "", limit: int = 5) -> list[dict]:
    """
    Search indexed files and workspace directories using the Search Policy Engine.
    Applies visibility metadata tags and filters out internal system runtime files
    unless Developer Mode is active.
    """
    query_clean = query.lower().strip()
    if query_clean.startswith("open "):
        query_clean = query_clean[5:].strip()

    words = [w for w in re.split(r'\W+', query_clean) if len(w) > 2]
    candidates: list[dict] = []
    dev_mode = is_developer_mode_active()

    # 1. Fetch from SQLite file_index table
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM file_index LIMIT 500;")
            rows = cursor.fetchall()
            for r in rows:
                candidates.append(dict(r))
    except Exception as e:
        print(f"[Filesystem] SQLite query note: {e}")

    # 2. Live scanning of active workspace & user directories
    scan_dirs = []
    if active_workspace and os.path.isdir(active_workspace):
        scan_dirs.append(active_workspace)
    
    user_home = Path.home()
    for sub in ["Downloads", "Documents", "Desktop"]:
        sp = user_home / sub
        if sp.exists() and str(sp) not in scan_dirs:
            scan_dirs.append(str(sp))

    for base_dir in scan_dirs:
        try:
            for root, _, files in os.walk(base_dir):
                # Skip internal system directories during scanning unless in Dev Mode
                if not dev_mode and any(x in root for x in [".git", "__pycache__", "node_modules", "temp_audio", "logs", "cache", "chroma_db"]):
                    continue
                for f in files[:50]:
                    full_p = os.path.join(root, f)
                    if not any(c["filepath"] == full_p for c in candidates):
                        try:
                            stat = os.stat(full_p)
                            candidates.append({
                                "id": full_p,
                                "filename": f,
                                "filepath": full_p,
                                "file_type": Path(f).suffix.lstrip("."),
                                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "size_bytes": stat.st_size,
                                "tags": "[]",
                                "workspace": base_dir
                            })
                        except Exception:
                            pass
        except Exception:
            pass

    if not candidates:
        return []

    # 3. Apply Search Policy Filtering (Visibility Layer)
    valid_candidates = []
    for item in candidates:
        fn = item["filename"]
        fp = item["filepath"]
        meta = classify_file_metadata(fp, fn)
        item.update(meta)

        # Policy Engine: In normal user mode, require visibility == "user" AND searchable == True
        if not dev_mode:
            if meta["visibility"] == "system" or not meta["searchable"]:
                # Exception: if query explicitly mentions full filename e.g. "noor.db"
                if query_clean.endswith(fn.lower()):
                    valid_candidates.append(item)
                continue

        valid_candidates.append(item)

    if not valid_candidates:
        return []

    # 4. Apply 4-Factor Weighted Ranking
    now_ts = datetime.now().timestamp()
    ranked_results = []

    for item in valid_candidates:
        fn = item["filename"].lower()
        fp = item["filepath"].lower()

        # Factor 1: Semantic / Keyword Similarity (40%)
        NOISE_SEARCH_WORDS = {"folder", "file", "directory", "dir", "from", "drive", "open", "in", "on", "the", "a", "an", "code"}
        filtered_words = [w for w in words if w not in NOISE_SEARCH_WORDS]
        if not filtered_words:
            filtered_words = words

        match_count = sum(1 for w in filtered_words if w in fn or w in fp)
        semantic_score = min(1.0, match_count / max(1, len(filtered_words))) * 40.0

        # Factor 2: Recency (30%)
        recency_score = 0.0
        try:
            mtime = datetime.fromisoformat(item["last_modified"]).timestamp()
            age_hours = max(0.1, (now_ts - mtime) / 3600.0)
            recency_score = max(0.0, 30.0 * (1.0 / (1.0 + (age_hours / 24.0))))
        except Exception:
            recency_score = 5.0

        # Factor 3: Workspace & Source Priority Relevance (20%)
        workspace_score = 0.0
        if active_workspace and active_workspace.lower() in fp:
            workspace_score = 20.0
        elif item.get("source") in ("documents", "downloads", "desktop"):
            workspace_score = 15.0

        # Factor 4: Exact Filename Match (10%)
        exact_score = 0.0
        if query_clean == fn or query_clean == os.path.splitext(fn)[0]:
            exact_score = 10.0
        elif query_clean in fn:
            exact_score = 5.0

        total_rank_score = semantic_score + recency_score + workspace_score + exact_score
        item["rank_score"] = round(total_rank_score, 2)
        ranked_results.append(item)

    ranked_results.sort(key=lambda x: x["rank_score"], reverse=True)
    return ranked_results[:limit]

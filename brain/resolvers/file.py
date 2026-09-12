"""
brain/resolvers/file.py
─────────────────────────────────────────────────────
File Resource Resolver.
Resolves file names, extensions, and documents using 4-factor weighted ranking.
Filters out internal database and binary files (.db, .sqlite, .pyc) unless explicitly named.
"""

import os
from typing import Dict, Any
from brain.resolvers.base import BaseResourceResolver, ResourceType
from brain.tools.filesystem import find_and_rank_files
from brain.system.workspace import get_active_workspace


class FileResolver(BaseResourceResolver):
    """Resource resolver for files and documents."""

    EXCLUDED_EXTENSIONS = [".db", ".sqlite", ".pyc", ".bin", ".dat", ".tmp", ".lock", ".log"]

    def match(self, target: str) -> float:
        ws = get_active_workspace()
        matches = find_and_rank_files(target, active_workspace=ws, limit=5)
        if matches:
            t_clean = target.lower().strip()
            if t_clean.startswith("open "):
                t_clean = t_clean[5:].strip()

            # If prompt asks for a folder or drive without explicit extension, defer to FolderResolver
            has_extension = bool(os.path.splitext(t_clean)[1])
            if any(x in t_clean for x in ["folder", "directory", "dir", "drive"]) and not has_extension:
                return 0.0

            # Filter out non-user binary files unless target explicitly mentions extension
            valid_matches = []
            for m in matches:
                ext = os.path.splitext(m["filename"])[1].lower()
                if ext in self.EXCLUDED_EXTENSIONS and not t_clean.endswith(ext):
                    continue
                valid_matches.append(m)

            if valid_matches:
                top_score = valid_matches[0].get("rank_score", 0.0)
                if top_score >= 50.0:
                    return 0.95
                elif top_score >= 25.0:
                    return 0.85
                return 0.60
        return 0.0

    def resolve(self, target: str) -> Dict[str, Any]:
        ws = get_active_workspace()
        matches = find_and_rank_files(target, active_workspace=ws, limit=5)
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        confidence = self.match(target)

        valid_matches = []
        if matches:
            for m in matches:
                ext = os.path.splitext(m["filename"])[1].lower()
                if ext in self.EXCLUDED_EXTENSIONS and not t_clean.endswith(ext):
                    continue
                valid_matches.append(m)

        if valid_matches:
            top = valid_matches[0]
            return {
                "resource_type": ResourceType.FILE,
                "confidence": confidence,
                "resolved_target": top["filepath"],
                "action": "open_file",
                "metadata": {
                    "filename": top["filename"],
                    "rank_score": top.get("rank_score", 0.0),
                    "workspace": ws
                }
            }

        return {
            "resource_type": ResourceType.UNKNOWN,
            "confidence": 0.0,
            "resolved_target": target,
            "action": "none",
            "metadata": {}
        }

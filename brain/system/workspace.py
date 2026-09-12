"""
brain/system/workspace.py
─────────────────────────────────────────────────────
Active Workspace Awareness & Developer Mode Scoping.
Maintains active development workspace (e.g. D:\\Noor) and Developer Mode state toggle.
"""

import os
from brain.db import get_db

_active_workspace: str = r"D:\Noor"
_developer_mode: bool = False


def set_active_workspace(workspace_path: str) -> bool:
    """Set the active development workspace directory."""
    global _active_workspace
    if not workspace_path or not os.path.exists(workspace_path):
        return False

    _active_workspace = os.path.abspath(workspace_path)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES ('active_workspace', ?, datetime('now'));",
                (_active_workspace,)
            )
    except Exception as e:
        print(f"[Workspace] Error saving preference: {e}")

    return True


def get_active_workspace() -> str:
    """Return the currently active development workspace directory path."""
    global _active_workspace
    try:
        with get_db() as conn:
            row = conn.execute("SELECT value FROM preferences WHERE key = 'active_workspace';").fetchone()
            if row and row[0] and os.path.exists(row[0]):
                _active_workspace = row[0]
    except Exception:
        pass
    return _active_workspace


def toggle_developer_mode(enabled: bool = True) -> bool:
    """Enable or disable Developer Mode (exposes system runtime logs, caches, and protected files)."""
    global _developer_mode
    _developer_mode = enabled
    print(f"[Workspace] Developer Mode set to: {_developer_mode}")
    return _developer_mode


def is_developer_mode_active() -> bool:
    """Return whether Developer Mode is currently active."""
    global _developer_mode
    return _developer_mode

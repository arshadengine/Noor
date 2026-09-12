"""
brain/project_engine.py
─────────────────────────────────────────────────────
Noor's Project Context Engine.

Manages the project registry, detects focused workspaces,
and loads relevant context files and git status.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from brain.os_agent import execute_safe_command
from brain.memory import set_preference, get_preference, save_proactive_suggestion

REGISTRY_PATH = Path("D:/Noor/configs/project_registry.json")


def load_registry() -> dict:
    """Load the project registry."""
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Create default registry
        default = {
            "TASKAS": {"path": "D:/TASKAS", "type": "React", "last_opened": "", "vector_db": ""},
            "Ridezy": {"path": "D:/Users/Arshad/AndroidStudioProjects/Ridezy", "type": "Android (Java/Kotlin)", "last_opened": "", "vector_db": ""},
            "Smart Presence": {"path": "D:/Users/Arshad/AndroidStudioProjects/SmartPresence", "type": "Flutter/Android", "last_opened": "", "vector_db": ""},
            "QuickServa": {"path": "D:/Quickserva", "type": "Python/Web", "last_opened": "", "vector_db": ""},
            "Noor": {"path": "D:/Noor", "type": "Python (AI Companion)", "last_opened": "", "vector_db": ""}
        }
        save_registry(default)
        return default
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ProjectEngine] Failed to load project registry: {e}")
        return {}


def save_registry(registry: dict) -> None:
    """Save the project registry."""
    try:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[ProjectEngine] Failed to save project registry: {e}")


def detect_active_project(win_title: str, app_name: str) -> dict | None:
    """
    Strictly detect if the user's active window matches a registered project.
    Matches folder paths or explicit project names in titles.
    """
    registry = load_registry()
    win_title_lower = win_title.lower()
    
    # Check each project in the registry
    for name, details in registry.items():
        path = details.get("path", "")
        path_obj = Path(path)
        
        # Match conditions:
        # 1. Project name exists in the window title (e.g. "TASKAS - Visual Studio Code")
        # 2. Window title contains the absolute folder path
        # 3. Path basename matches the folder name in focus
        path_basename = path_obj.name.lower()
        
        is_match = False
        if name.lower() in win_title_lower:
            is_match = True
        elif path_basename in win_title_lower:
            is_match = True
        elif path.lower() in win_title_lower.replace("\\", "/"):
            is_match = True
            
        if is_match and path_obj.exists():
            # Update last opened time
            details["last_opened"] = datetime.utcnow().isoformat()
            save_registry(registry)
            return {"name": name, "path": path, "type": details.get("type", "Unknown")}
            
    return None


def load_project_context(project_name: str) -> str:
    """
    Load architectural and status context for a specific project.
    Reads README, TODOs, architecture docs, and runs git status.
    """
    registry = load_registry()
    project = registry.get(project_name)
    if not project:
        return f"⚠️ Project '{project_name}' is not registered."
        
    path_str = project.get("path", "")
    path = Path(path_str)
    if not path.exists():
        return f"⚠️ Project path '{path_str}' does not exist on disk."
        
    context = [f"### Project Context: {project_name} ({project.get('type', 'Unknown')})"]
    context.append(f"Directory Path: `{path_str}`")
    
    # 1. Read README or Architecture docs (limit size)
    for doc_name in ("README.md", "README.txt", "architecture.md", "todo.md", "todo.txt", "TODO.md"):
        doc_path = path / doc_name
        if doc_path.exists():
            try:
                content = doc_path.read_text(encoding="utf-8", errors="replace")
                truncated = content[:1500] + "\n[... truncated ...]" if len(content) > 1500 else content
                context.append(f"\n--- {doc_name} ---\n{truncated}")
                break # Only read first matching doc to avoid clutter
            except Exception as e:
                print(f"[ProjectEngine] Failed to read {doc_name}: {e}")
                
    # 2. Run Git Status to understand current branch and modification state
    try:
        # Run git status using -C option
        git_res = execute_safe_command(f"git -C \"{path_str}\" status -s")
        if git_res and not git_res.startswith("❌") and not "not a git repository" in git_res.lower():
            # Check branch
            branch_res = execute_safe_command(f"git -C \"{path_str}\" branch --show-current")
            branch = branch_res.strip() if branch_res and not branch_res.startswith("❌") else "unknown"
            context.append(f"\n--- Git Status (Branch: {branch}) ---\n{git_res}")
        else:
            context.append("\n--- Git Status ---\nNot a Git repository or Git not initialized.")
    except Exception as e:
        context.append(f"\n--- Git Status ---\nFailed to retrieve: {e}")
        
    context_str = "\n".join(context)
    
    # Cache active context in preferences
    set_preference("active_project", project_name)
    set_preference("active_project_path", path_str)
    set_preference("active_project_context", context_str)
    
    return context_str

"""
brain/proactive_daemon.py
─────────────────────────────────────────────────────
Noor's Background Proactive Daemon.

Monitors event sources (clipboard, downloads, active windows) and uses
the reasoning engine to log proactive suggestions and context updates.
"""

from __future__ import annotations

import os
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta

from brain.llm import simple_query
from brain.memory import save_proactive_suggestion, log_agent_action, set_preference, get_preference
from brain.os_agent import get_clipboard_text, get_focused_app_and_title, safe_read_file, execute_safe_command

# Thread management
_stop_event = threading.Event()
_daemon_thread = None

# Monitors state
_seen_downloads: set[str] = set()
_last_clipboard_text: str = ""
_last_workspace_time: datetime = datetime.min
_current_active_workspace: str = ""


def seed_existing_downloads(downloads_dir: Path) -> None:
    """Pre-seed existing downloads so we only flag *new* files."""
    if not downloads_dir.exists():
        return
    try:
        for item in downloads_dir.iterdir():
            if item.is_file():
                _seen_downloads.add(str(item.resolve()))
    except Exception as e:
        print(f"[Proactive Daemon] Error seeding downloads: {e}")


def check_new_downloads(downloads_dir: Path) -> None:
    """Scan Downloads for newly added documents and trigger summarization."""
    if not downloads_dir.exists():
        return
        
    try:
        for item in downloads_dir.iterdir():
            if not item.is_file():
                continue
                
            file_path_str = str(item.resolve())
            if file_path_str in _seen_downloads:
                continue
                
            # Found a new file!
            _seen_downloads.add(file_path_str)
            suffix = item.suffix.lower()
            
            # Watch for document types
            if suffix in (".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json"):
                # Wait briefly to make sure the file is fully written/downloaded
                time.sleep(1.0)
                
                filename = item.name
                print(f"[Proactive Daemon] Detected new download: {filename}")
                log_agent_action("ProactiveDaemon", f"New file downloaded: {filename}")
                
                # Read content
                content = safe_read_file(file_path_str)
                if content.startswith("❌") or content.startswith("⚠️"):
                    # Failed to read or empty
                    continue
                    
                # Reason and summarize
                system_prompt = (
                    "You are Noor's proactive document indexer.\n"
                    "Provide a very concise summary (2 sentences maximum) of the downloaded file.\n"
                    "Identify 3 key topics or keywords."
                )
                prompt = f"Document Name: {filename}\nContent:\n{content[:2500]}"
                
                try:
                    summary = simple_query(prompt, system_prompt)
                    
                    # Save proactive suggestion
                    title = f"New Document Downloaded: {filename}"
                    suggestion_content = (
                        f"I noticed you downloaded a new file: **{filename}**.\n\n"
                        f"**Summary:**\n{summary}\n\n"
                        f"I have automatically added this to your knowledge references."
                    )
                    
                    save_proactive_suggestion(
                        title=title,
                        content=suggestion_content,
                        event_type="download",
                        action_data={"filepath": file_path_str, "filename": filename}
                    )
                    log_agent_action("ProactiveDaemon", f"Created suggestion for download: {filename}")
                except Exception as query_err:
                    print(f"[Proactive Daemon] Failed to query LLM for download summary: {query_err}")
                    
    except Exception as e:
        print(f"[Proactive Daemon] Error in downloads watcher: {e}")


def is_source_code(text: str) -> bool:
    """Heuristic to check if a block of text looks like source code."""
    # Common code markers
    code_indicators = [
        "def ", "class ", "import ", "const ", "let ", "function ", "func ",
        "public class", "void ", "return ", "using ", "include <", "package "
    ]
    text_lower = text.lower()
    
    # Check for keywords
    has_keyword = any(ind in text for ind in code_indicators) or any(ind in text_lower for ind in code_indicators)
    
    # Check for brackets/braces/indentation structure
    has_braces = "{" in text and "}" in text
    has_indent = "\n    " in text or "\n\t" in text
    
    return has_keyword or (has_braces and has_indent)


def check_clipboard_changes() -> None:
    """Monitor clipboard for code copies and suggest explanations/optimizations."""
    global _last_clipboard_text
    try:
        clip_text = get_clipboard_text()
        if not clip_text or not clip_text.strip():
            return
            
        # Ignore if it hasn't changed or is too short to be interesting
        if clip_text == _last_clipboard_text or len(clip_text) < 80:
            return
            
        _last_clipboard_text = clip_text
        
        # Check if it looks like code
        if is_source_code(clip_text):
            print("[Proactive Daemon] Detected code block copied to clipboard.")
            log_agent_action("ProactiveDaemon", "Code block copied to clipboard.")
            
            system_prompt = (
                "You are Noor's proactive developer companion.\n"
                "Review the copied code block. Provide a brief 1-sentence description of what it does,\n"
                "and list 1 quick optimization, bug fix, or best practice tip."
            )
            prompt = f"Analyze this copied code:\n\n{clip_text[:2000]}"
            
            try:
                explanation = simple_query(prompt, system_prompt)
                
                title = "Code Copied to Clipboard"
                suggestion_content = (
                    "I noticed you copied a block of code to your clipboard. Here is a quick analysis:\n\n"
                    f"{explanation}\n\n"
                    "Would you like me to refactor or write unit tests for this code?"
                )
                
                save_proactive_suggestion(
                    title=title,
                    content=suggestion_content,
                    event_type="clipboard",
                    action_data={"text": clip_text}
                )
                log_agent_action("ProactiveDaemon", "Created suggestion for copied code.")
            except Exception as query_err:
                print(f"[Proactive Daemon] Failed to query LLM for clipboard code: {query_err}")
                
    except Exception as e:
        print(f"[Proactive Daemon] Error in clipboard watcher: {e}")


def check_active_workspace() -> None:
    """Monitor active window for developer workspaces (e.g. TASKAS, Noor in VS Code)."""
    global _last_workspace_time, _current_active_workspace
    
    now = datetime.now()
    # Limit workspace updates to once every 5 minutes to avoid spamming
    if now - _last_workspace_time < timedelta(minutes=5):
        return
        
    try:
        win_info = get_focused_app_and_title()
        title = win_info.get("title", "")
        app = win_info.get("app", "")
        
        is_dev_app = any(name in app.lower() for name in ("code", "cmd", "powershell", "terminal", "idea", "pycharm"))
        if not is_dev_app:
            return
            
        from brain.project_engine import detect_active_project, load_project_context
        active_proj = detect_active_project(title, app)
        
        if active_proj:
            _last_workspace_time = now
            project_name = active_proj["name"]
            workspace_path = active_proj["path"]
            
            # If we've already registered this active workspace recently, skip
            if _current_active_workspace == workspace_path:
                return
                
            _current_active_workspace = workspace_path
            print(f"[Proactive Daemon] Loaded development context for project: {project_name}")
            log_agent_action("ProactiveDaemon", f"Workspace focused: {project_name} at {workspace_path}")
            
            # Load project context
            context_str = load_project_context(project_name)
            
            # Get summary of git status if git exists
            git_status = get_preference("active_workspace_status", "")
            if not git_status and "Git Status" in context_str:
                parts = context_str.split("--- Git Status")
                if len(parts) > 1:
                    git_status = parts[1].strip(" -").strip()
            
            system_prompt = (
                f"You are Noor's workspace assistant for the project '{project_name}'.\n"
                "Given the short project files or git status summary, write a 1-sentence status of what the developer is doing.\n"
                "Keep it brief."
            )
            prompt = f"Project Context:\n{context_str[:2500]}"
            
            try:
                status_summary = simple_query(prompt, system_prompt)
                
                title = f"{project_name} Workspace Loaded"
                suggestion_content = (
                    f"I see you're working on the **{project_name}** project.\n\n"
                    f"**Current Status:**\n{status_summary}\n\n"
                    f"I have loaded this project context. You can now ask me questions directly about the files."
                )
                
                save_proactive_suggestion(
                    title=title,
                    content=suggestion_content,
                    event_type="workspace",
                    action_data={"workspace_path": workspace_path, "project_name": project_name}
                )
                log_agent_action("ProactiveDaemon", f"Created suggestion for workspace: {project_name}")
            except Exception as query_err:
                print(f"[Proactive Daemon] Failed to query LLM for workspace status: {query_err}")
                
        else:
            # Clear active workspace if user switched away to another project
            if _current_active_workspace:
                _current_active_workspace = ""
                set_preference("active_project", "")
                set_preference("active_project_path", "")
                set_preference("active_project_context", "")
                set_preference("active_workspace", "")
                set_preference("active_workspace_status", "")
                
    except Exception as e:
        print(f"[Proactive Daemon] Error in workspace watcher: {e}")


def daemon_loop() -> None:
    """Main execution loop for the proactive daemon."""
    downloads_dir = Path("C:/Users/Arshad/Downloads")
    seed_existing_downloads(downloads_dir)
    
    print("[Noor Proactive Daemon] Background Proactive Daemon started.")
    log_agent_action("ProactiveDaemon", "Background Proactive Daemon started.")
    
    # Run loop
    downloads_counter = 0
    workspace_counter = 0
    
    while not _stop_event.is_set():
        try:
            # Check clipboard changes frequently (every 1 second)
            check_clipboard_changes()
            
            # Check downloads occasionally (every 5 seconds)
            downloads_counter += 1
            if downloads_counter >= 5:
                check_new_downloads(downloads_dir)
                downloads_counter = 0
                
            # Check workspace focus occasionally (every 10 seconds)
            workspace_counter += 1
            if workspace_counter >= 10:
                check_active_workspace()
                workspace_counter = 0
                
        except Exception as e:
            print(f"[Proactive Daemon] Error in main loop iteration: {e}")
            
        _stop_event.wait(timeout=1.0)


def start_proactive_daemon() -> None:
    """Start the background proactive daemon thread."""
    global _daemon_thread
    if _daemon_thread is not None and _daemon_thread.is_alive():
        return
        
    _stop_event.clear()
    _daemon_thread = threading.Thread(target=daemon_loop, name="NoorProactiveDaemon", daemon=True)
    _daemon_thread.start()


def stop_proactive_daemon() -> None:
    """Stop the background proactive daemon thread."""
    global _daemon_thread
    _stop_event.set()
    if _daemon_thread:
        _daemon_thread.join(timeout=3.0)
        _daemon_thread = None
        print("[Noor Proactive Daemon] Proactive Daemon stopped.")

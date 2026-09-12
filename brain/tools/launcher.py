"""
brain/tools/launcher.py
─────────────────────────────────────────────────────
Native Application Launcher.
Launches Windows applications cleanly via direct .exe paths, shortcuts, or UWP shell URIs.
"""

import os
import subprocess
from brain.memory import log_agent_action


def launch_application(executable_path: str, app_name: str = "") -> str:
    """Launch an application given an executable path, shortcut, or UWP shell URI."""
    if not executable_path:
        return "❌ Cannot launch application: Path is empty."

    display_name = app_name if app_name else os.path.basename(executable_path)

    # Handle Windows Store / UWP Apps shell URI
    if executable_path.startswith("shell:AppsFolder\\"):
        try:
            subprocess.Popen(["explorer.exe", executable_path])
            msg = f"✅ Successfully launched UWP application: {display_name} ({executable_path})"
            log_agent_action("Launcher", msg)
            return msg
        except Exception as e:
            err = f"❌ Failed to launch UWP app {display_name}: {e}"
            log_agent_action("Launcher", err)
            return err

    if not os.path.exists(executable_path):
        err = f"❌ Cannot launch application: Path '{executable_path}' does not exist."
        log_agent_action("Launcher", err)
        return err

    try:
        if hasattr(os, "startfile"):
            os.startfile(executable_path)
        else:
            subprocess.Popen([executable_path])
        
        msg = f"✅ Successfully launched {display_name} ({executable_path})"
        log_agent_action("Launcher", msg)
        return msg
    except Exception as e:
        err = f"❌ Failed to launch {display_name}: {e}"
        log_agent_action("Launcher", err)
        return err

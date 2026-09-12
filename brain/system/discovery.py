"""
brain/system/discovery.py
─────────────────────────────────────────────────────
Incremental Application Discovery & Multi-Tag Classification.
Scans Windows shortcuts, registry app paths, Get-StartApps UWP packages, and PATH executables.
Caches installed apps into SQLite installed_applications table for 0ms startup.
"""

import os
import json
import winreg
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from brain.db import get_db

# Pre-defined Multi-Tag Map for popular Windows software
APP_TAG_MAP = {
    "code.exe": ["IDE", "Programming", "Python", "Java", "Editor", "Git", "Code", "Development"],
    "code.cmd": ["IDE", "Programming", "Python", "Java", "Editor", "Git", "Code", "Development"],
    "chrome.exe": ["Browser", "Internet", "Web", "Google", "Search"],
    "brave.exe": ["Browser", "Internet", "Web", "Privacy", "Brave"],
    "msedge.exe": ["Browser", "Internet", "Web", "Microsoft", "Edge"],
    "firefox.exe": ["Browser", "Internet", "Web", "Mozilla", "Firefox"],
    "wt.exe": ["Terminal", "Console", "Shell", "Command", "Powershell", "CLI"],
    "cmd.exe": ["Terminal", "Console", "Command Prompt", "CLI"],
    "powershell.exe": ["Terminal", "Console", "Powershell", "CLI"],
    "spotify.exe": ["Media", "Music", "Audio", "Songs", "Player"],
    "vlc.exe": ["Media", "Music", "Video", "Player", "Movies"],
    "mspaint.exe": ["Editor", "Image", "Paint", "Drawing", "Graphics"],
    "photoshop.exe": ["Editor", "Image", "Photoshop", "Graphics", "Design"],
    "notepad.exe": ["Editor", "Text", "Notes", "Draft"],
    "calc.exe": ["Utility", "Calculator", "Math"],
    "taskmgr.exe": ["Utility", "Task Manager", "System", "Processes"],
}


def _is_blacklisted_app(name: str, exe: str) -> bool:
    """Filter out background CLI helpers, message hosts, updaters, installers, and CLI daemons."""
    n = name.lower()
    e = exe.lower()
    blacklist_words = [
        "messagehost", "nativehost", "helper", "installer", "uninstaller",
        "updater", "service", "daemon", "driver", "background", "crashpad",
        "setup.exe", "uninstall.exe", "pad.browsernativemessagehost", "_cli", "cli.exe"
    ]
    return any(b in n or b in e for b in blacklist_words)


def scan_and_register_applications(force_refresh: bool = False) -> int:
    """
    Scan Start Menu, Desktop shortcuts, Registry, Get-StartApps, and PATH for installed apps.
    Saves/updates SQLite installed_applications table.
    """
    if not force_refresh:
        try:
            with get_db() as conn:
                count = conn.execute("SELECT COUNT(*) FROM installed_applications;").fetchone()[0]
                if count > 5:
                    return count
        except Exception:
            pass

    found_apps: dict[str, dict] = {}

    # 1. Known Drive D: and C: GUI Applications (VS Code, Chrome, Terminal, Brave, Edge)
    known_executables = [
        ("visual_studio_code", "Visual Studio Code", "Code.exe", r"D:\Users\Arshad\AppData\Local\Programs\Microsoft VS Code\Code.exe"),
        ("windows_terminal", "Windows Terminal", "wt.exe", r"C:\Users\Arshad\AppData\Local\Microsoft\WindowsApps\wt.exe"),
        ("chrome", "Google Chrome", "chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ("brave", "Brave Browser", "brave.exe", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ("edge", "Microsoft Edge", "msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ("android_studio", "Android Studio", "studio64.exe", r"D:\Program Files\Android\Android Studio2\bin\studio64.exe"),
    ]
    for clean_id, name, exe, p in known_executables:
        if os.path.exists(p):
            found_apps[clean_id] = {
                "app_id": clean_id,
                "name": name,
                "exe_name": exe,
                "path": p,
                "category": _categorize_app(name, exe),
                "tags": _get_app_tags(name, exe),
                "aliases": [name.lower(), "code", "ide", "vscode", "vs code"] if "code" in clean_id else [name.lower()]
            }

    # 2. Get-StartApps UWP Package Discovery (Spotify, Windows Apps)
    try:
        ps_cmd = "powershell -Command \"Get-StartApps | ConvertTo-Json\""
        ps_out = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, errors="ignore").stdout
        if ps_out and (ps_out.strip().startswith("[") or ps_out.strip().startswith("{")):
            apps_data = json.loads(ps_out, strict=False)
            if isinstance(apps_data, dict):
                apps_data = [apps_data]
            for app in apps_data:
                name = app.get("Name", "").strip()
                app_id_raw = app.get("AppID", "").strip()
                if name and app_id_raw:
                    if _is_blacklisted_app(name, app_id_raw):
                        continue
                    clean_id = name.lower().replace(" ", "_")
                    if clean_id not in found_apps:
                        launch_p = app_id_raw if os.path.exists(app_id_raw) else f"shell:AppsFolder\\{app_id_raw}"
                        found_apps[clean_id] = {
                            "app_id": clean_id,
                            "name": name,
                            "exe_name": f"{name}.exe",
                            "path": launch_p,
                            "category": _categorize_app(name, app_id_raw),
                            "tags": _get_app_tags(name, app_id_raw),
                            "aliases": [name.lower(), clean_id]
                        }
    except Exception as e:
        print(f"[AppDiscovery] Get-StartApps note: {e}")

    # 3. Start Menu Shortcuts (.lnk)
    start_menu_paths = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
    ]
    for smp in start_menu_paths:
        if os.path.exists(smp):
            for root, _, files in os.walk(smp):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        app_name = os.path.splitext(f)[0]
                        if _is_blacklisted_app(app_name, f"{app_name}.exe"):
                            continue
                        clean_id = app_name.lower().replace(" ", "_")
                        lnk_path = os.path.join(root, f)
                        if clean_id not in found_apps:
                            found_apps[clean_id] = {
                                "app_id": clean_id,
                                "name": app_name,
                                "exe_name": f"{app_name}.exe",
                                "path": lnk_path,
                                "category": _categorize_app(app_name, f"{app_name}.exe"),
                                "tags": _get_app_tags(app_name, f"{app_name}.exe"),
                                "aliases": [app_name.lower(), clean_id]
                            }

    # 4. Registry App Paths
    registry_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
    ]
    for hkey, subkey in registry_keys:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                info = winreg.QueryInfoKey(key)
                for i in range(info[0]):
                    reg_name = winreg.EnumKey(key, i)
                    try:
                        with winreg.OpenKey(key, reg_name) as sub_k:
                            raw_path, _ = winreg.QueryValueEx(sub_k, "")
                            raw_path = os.path.expandvars(raw_path).strip('"')
                            if os.path.exists(raw_path):
                                name_no_ext = os.path.splitext(reg_name)[0]
                                if _is_blacklisted_app(name_no_ext, reg_name):
                                    continue
                                clean_id = name_no_ext.lower().replace(" ", "_")
                                if clean_id not in found_apps:
                                    found_apps[clean_id] = {
                                        "app_id": clean_id,
                                        "name": name_no_ext.title(),
                                        "exe_name": reg_name,
                                        "path": raw_path,
                                        "category": _categorize_app(name_no_ext, reg_name),
                                        "tags": _get_app_tags(name_no_ext, reg_name),
                                        "aliases": [name_no_ext.lower(), reg_name.lower()]
                                    }
                    except Exception:
                        pass
        except Exception:
            pass

    # Save to SQLite database
    now_iso = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("DELETE FROM installed_applications;")
        for app in found_apps.values():
            conn.execute("""
                INSERT OR REPLACE INTO installed_applications
                (app_id, name, exe_name, path, category, tags, aliases, last_scanned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                app["app_id"],
                app["name"],
                app["exe_name"],
                app["path"],
                app["category"],
                json.dumps(app["tags"]),
                json.dumps(app["aliases"]),
                now_iso
            ))

    print(f"[AppDiscovery] Registered {len(found_apps)} clean GUI applications into SQLite database.")
    return len(found_apps)


def get_application_by_query(query: str) -> dict | None:
    """
    Find best matching application using exact name, alias, category, or multi-tag search.
    Supports intent queries like "Launch my IDE" -> VS Code, "Open my browser" -> Chrome/Brave, "Open Spotify" -> Spotify.
    """
    scan_and_register_applications(force_refresh=False)
    q_clean = query.lower().strip()

    # Intent synonyms map
    synonyms = {
        "ide": ["ide", "editor", "coding", "programming", "code", "vs code", "vscode", "android studio"],
        "browser": ["browser", "web", "internet", "chrome", "brave", "edge", "firefox"],
        "terminal": ["terminal", "console", "command prompt", "powershell", "cmd"],
        "media": ["media", "music", "songs", "audio", "spotify", "vlc"],
        "editor": ["editor", "paint", "photoshop", "text", "notepad"]
    }

    matching_tags = [q_clean]
    for cat, syn_list in synonyms.items():
        if any(s in q_clean for s in syn_list):
            matching_tags.append(cat)

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM installed_applications;").fetchall()
        best_match = None
        best_score = 0

        for r in rows:
            app = dict(r)
            if _is_blacklisted_app(app["name"], app["exe_name"]):
                continue

            tags = json.loads(app.get("tags") or "[]")
            aliases = json.loads(app.get("aliases") or "[]")
            name_lower = app["name"].lower()
            exe_lower = app["exe_name"].lower()
            cat_lower = app["category"].lower()

            score = 0
            # Primary GUI App Boost
            if exe_lower in ["brave.exe", "chrome.exe", "msedge.exe", "firefox.exe"] and "browser" in matching_tags:
                score += 200
            elif exe_lower in ["code.exe", "code.cmd", "studio64.exe"] and "ide" in matching_tags:
                score += 200
            elif exe_lower in ["wt.exe", "cmd.exe", "powershell.exe"] and "terminal" in matching_tags:
                score += 200
            elif "spotify" in q_clean and "spotify" in name_lower:
                score += 300

            if q_clean == name_lower or q_clean == exe_lower:
                score += 150
            elif any(q_clean in a for a in aliases):
                score += 100
            elif any(t.lower() in q_clean or q_clean in t.lower() for t in tags):
                score += 60
            elif cat_lower in q_clean or any(m in cat_lower for m in matching_tags):
                score += 40

            if score > best_score:
                best_score = score
                best_match = app

        if best_match and best_score >= 30:
            return best_match

    return None


def _categorize_app(name: str, exe: str = "") -> str:
    n = name.lower()
    e = exe.lower()
    if any(x in e or x in n for x in ["chrome", "brave", "firefox", "msedge", "edge"]):
        return "browser"
    if any(x in e or x in n for x in ["code", "studio", "pycharm", "intellij", "sublime"]):
        return "ide"
    if any(x in e or x in n for x in ["wt.exe", "windows terminal", "cmd.exe", "powershell", "console"]):
        return "terminal"
    if any(x in e or x in n for x in ["spotify", "vlc", "player", "media"]):
        return "media"
    if any(x in e or x in n for x in ["paint", "photoshop", "gimp", "draw"]):
        return "editor"
    return "utility"


def _get_app_tags(name: str, exe: str) -> list[str]:
    exe_key = exe.lower()
    if exe_key in APP_TAG_MAP:
        return APP_TAG_MAP[exe_key]
    return [name.title(), _categorize_app(name, exe).title()]

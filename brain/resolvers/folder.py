"""
brain/resolvers/folder.py
─────────────────────────────────────────────────────
Folder & Directory Resource Resolver.
Dynamically queries Windows Registry User Shell Folders to resolve relocated directories
(e.g., D:\\Users\\Arshad\\Downloads or OneDrive\\Desktop).
Performs dynamic drive scanning (e.g., "Projects folder from d drive" -> D:\\Projects).
"""

import os
import re
import winreg
from typing import Dict, Any
from brain.resolvers.base import BaseResourceResolver, ResourceType
from brain.system.workspace import get_active_workspace


def get_windows_shell_folder(name: str) -> str:
    """Dynamically query Windows Registry User Shell Folders for relocated user directories."""
    n_clean = name.lower().strip()
    for noise in ["folder", "my ", "windows "]:
        n_clean = n_clean.replace(noise, "").strip()

    key_name_map = {
        "downloads": ["{374DE290-123F-4565-9164-39C4925E467B}", "{7D8300DF-3770-439F-8576-561A72612B04}"],
        "download": ["{374DE290-123F-4565-9164-39C4925E467B}", "{7D8300DF-3770-439F-8576-561A72612B04}"],
        "documents": ["Personal"],
        "document": ["Personal"],
        "desktop": ["Desktop"],
        "pictures": ["My Pictures"],
        "music": ["My Music"],
        "videos": ["My Video"]
    }

    reg_keys = key_name_map.get(n_clean, [])
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            for k in reg_keys:
                try:
                    val, _ = winreg.QueryValueEx(key, k)
                    expanded = os.path.expandvars(val)
                    if expanded and os.path.exists(expanded):
                        return expanded
                except Exception:
                    pass
    except Exception:
        pass

    # Fallbacks across drives C: and D:
    drive_fallbacks = [
        rf"D:\Users\Arshad\{n_clean.title()}",
        rf"D:\{n_clean.title()}",
        rf"C:\Users\Arshad\{n_clean.title()}",
        os.path.expandvars(rf"%USERPROFILE%\{n_clean.title()}")
    ]
    for p in drive_fallbacks:
        if os.path.exists(p):
            return p

    return os.path.expandvars(rf"%USERPROFILE%\{n_clean.title()}")


class FolderResolver(BaseResourceResolver):
    """Resource resolver for folders and directories."""

    def match(self, target: str) -> float:
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        for key in ["download", "document", "desktop", "picture", "music", "video", "workspace", "project"]:
            if key in t_clean:
                return 0.95

        # Explicit folder / drive keywords ("folder", "directory", "d drive", "c drive")
        if any(x in t_clean for x in ["folder", "directory", "dir", "drive"]):
            return 0.98

        if os.path.isabs(target) and os.path.isdir(target):
            return 0.98

        return 0.0

    def resolve(self, target: str) -> Dict[str, Any]:
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        confidence = self.match(target)
        resolved_path = None

        # 1. Standard Windows Shell Folders (Downloads, Documents, Desktop)
        if any(x in t_clean for x in ["download", "document", "desktop", "picture", "music", "video"]):
            resolved_path = get_windows_shell_folder(t_clean)
        # 2. Absolute Path
        elif os.path.isabs(target) and os.path.isdir(target):
            resolved_path = target

        # 3. Dynamic Drive & File System Directory Search (e.g., "Projects folder from d drive" -> D:\Projects)
        if not resolved_path:
            target_name = re.sub(r"\b(?:from|on|in|the)\b", "", t_clean, flags=re.IGNORECASE)
            target_name = re.sub(r"\b[a-z]\s+drive\b", "", target_name, flags=re.IGNORECASE)
            target_name = re.sub(r"\b(?:drive|folder|directory|dir)\b", "", target_name, flags=re.IGNORECASE)
            target_name = re.sub(r"\b[a-z]:\b", "", target_name, flags=re.IGNORECASE)
            target_name = target_name.strip()

            drive_match = re.search(r"\b([a-zA-Z])\s*drive\b", target, re.IGNORECASE) or re.search(r"\b([a-zA-Z]):\b", target)
            drive_letter = drive_match.group(1).upper() if drive_match else None
            search_drives = [f"{drive_letter}:\\"] if drive_letter else ["D:\\", "C:\\"]

            for drive in search_drives:
                if os.path.exists(drive):
                    try:
                        # Direct exact check e.g. D:\Projects
                        direct_p = os.path.join(drive, target_name)
                        if target_name and os.path.isdir(direct_p):
                            resolved_path = direct_p
                            break

                        # Substring search across drive root
                        for item in os.listdir(drive):
                            full_item = os.path.join(drive, item)
                            if os.path.isdir(full_item):
                                if target_name and target_name.lower() == item.lower():
                                    resolved_path = full_item
                                    break
                                elif target_name and target_name.lower() in item.lower() and not resolved_path:
                                    resolved_path = full_item
                    except Exception:
                        pass
                if resolved_path:
                    break

        # 4. Fallback to Active Workspace only if explicitly requested or no specific folder found
        if not resolved_path:
            if any(x in t_clean for x in ["workspace", "active workspace", "noor project", "noor folder"]):
                resolved_path = get_active_workspace()

        if resolved_path and os.path.exists(resolved_path):
            return {
                "resource_type": ResourceType.FOLDER,
                "confidence": confidence,
                "resolved_target": resolved_path,
                "action": "open_folder",
                "metadata": {
                    "folder_name": os.path.basename(resolved_path)
                }
            }

        return {
            "resource_type": ResourceType.UNKNOWN,
            "confidence": 0.0,
            "resolved_target": target,
            "action": "none",
            "metadata": {}
        }

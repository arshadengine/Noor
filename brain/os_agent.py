"""
brain/os_agent.py
─────────────────────────────────────────────────────
Noor's OS Control Agent.

Handles safe shell command execution, opening desktop applications,
and GUI controls (keyboard/mouse) using pyautogui.
"""

from __future__ import annotations

import os
import sys
import subprocess
import webbrowser
import shlex
import ctypes
from brain.memory import log_agent_action

# Try to import pyautogui (will load if installed)
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


# A strict list of blocked command keywords to prevent accidental data loss/compromise
BLOCKED_KEYWORDS = [
    "del ", "rm ", "rmdir", "rd ", "format", "shutdown", "restart",
    "mkfs", "fdisk", "reg ", "attrib", "kill", "taskkill", "attrib"
]

# A whitelist of common windows executables we can launch safely
APP_MAP = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "explorer": "explorer.exe",
    "browser": "chrome.exe",
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "edge": "msedge.exe",
    "control": "control.exe",
    "control panel": "control.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "code": "Code.exe",
    "terminal": "wt.exe",
    "wt": "wt.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
}

SETTINGS_MAP = {
    "settings": "ms-settings:",
    "settings app": "ms-settings:",
    "bluetooth": "ms-settings:bluetooth",
    "wifi": "ms-settings:network-wifi",
    "wi-fi": "ms-settings:network-wifi",
    "network": "ms-settings:network",
    "sound": "ms-settings:sound",
    "volume": "ms-settings:sound",
    "display": "ms-settings:display",
    "apps": "ms-settings:appsfeatures",
    "update": "ms-settings:windowsupdate",
    "updates": "ms-settings:windowsupdate",
}

from brain.resolvers.folder import get_windows_shell_folder

class DynamicFolderMap(dict):
    def get(self, key, default=None):
        k_clean = str(key).lower().strip()
        if k_clean in ["noor", "project", "project folder"]:
            return "D:/Noor"
        try:
            folder = get_windows_shell_folder(k_clean)
            if folder and os.path.exists(folder):
                return folder
        except Exception:
            pass
        return super().get(key, default)

FOLDER_MAP = DynamicFolderMap({
    "downloads": get_windows_shell_folder("downloads"),
    "desktop": get_windows_shell_folder("desktop"),
    "documents": get_windows_shell_folder("documents"),
    "noor": "D:/Noor",
    "project": "D:/Noor",
    "project folder": "D:/Noor",
})


def is_safe_command(cmd: str) -> bool:
    """Verify if a shell command is safe to run."""
    cmd_lower = cmd.lower().strip()
    
    # Check against blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        if keyword in cmd_lower:
            return False
            
    # Block redirection and pipes to prevent writing files or chaining commands
    if ">" in cmd or "|" in cmd:
        return False
        
    # Allow common read-only or diagnostic commands
    safe_prefixes = [
        "dir", "ls", "echo", "systeminfo", "tasklist", "ipconfig",
        "ping", "get-childitem", "git status", "git log", "type ", "cat "
    ]
    
    for prefix in safe_prefixes:
        if cmd_lower.startswith(prefix):
            return True
            
    return True


def execute_safe_command(cmd: str) -> str:
    """Execute a shell command safely and return stdout/stderr."""
    log_agent_action("OSAgent", f"Executing shell command: '{cmd}'")
    
    if not is_safe_command(cmd):
        err = "⚠️ [OSAgent Security] Command rejected: contains blocked keywords or is unsafe."
        log_agent_action("OSAgent", "Command rejected for safety reasons.", err)
        return err
        
    try:
        # Use shell=True for windows cmd/powershell built-ins like 'dir'
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10.0,
            encoding="utf-8",
            errors="replace"
        )
        
        output = res.stdout if res.returncode == 0 else res.stderr
        if not output.strip():
            output = f"Command executed successfully (exit code {res.returncode}), but returned no output."
            
        log_agent_action("OSAgent", "Shell command executed successfully.", f"Exit code: {res.returncode}")
        return output
        
    except subprocess.TimeoutExpired:
        log_agent_action("OSAgent", "Command execution timed out.")
        return "⚠️ [OSAgent Error] Command execution timed out (limit: 10s)."
    except Exception as e:
        log_agent_action("OSAgent", f"Command failed: {e}")
        return f"❌ [OSAgent Error] Command failed: {e}"


def find_and_open_installed_app(app_name: str) -> str:
    """
    Dynamically search Windows Registry App Paths and Start Menu Programs
    shortcuts to locate and launch any installed application on the device.
    """
    import winreg
    import os
    import subprocess
    import shutil
    
    app_clean = app_name.lower().strip()
    
    # 1. Search in Registry App Paths
    registry_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
    ]
    
    for hkey, subkey in registry_keys:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                info = winreg.QueryInfoKey(key)
                for i in range(info[0]):
                    name = winreg.EnumKey(key, i)
                    name_no_ext = os.path.splitext(name)[0].lower()
                    if app_clean == name_no_ext or app_clean == name.lower():
                        try:
                            with winreg.OpenKey(key, name) as sub_k:
                                path, _ = winreg.QueryValueEx(sub_k, "")
                                path = os.path.expandvars(path)
                                path = path.strip('"')
                                if os.path.exists(path):
                                    subprocess.Popen(path)
                                    return f"✅ Successfully opened application: {name} (Registry Path: {path})"
                        except Exception:
                            pass
        except Exception:
            pass
            
    # 2. Search Start Menu shortcuts (.lnk files)
    start_menu_paths = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
    ]
    
    for base_path in start_menu_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        file_no_ext = os.path.splitext(file)[0].lower()
                        if app_clean == file_no_ext or app_clean in file_no_ext or file_no_ext in app_clean:
                            lnk_path = os.path.join(root, file)
                            try:
                                os.startfile(lnk_path)
                                return f"✅ Successfully opened application shortcut: {file}"
                            except Exception as e:
                                pass
                                
    # 3. Search in system PATH
    executable = shutil.which(app_name) or shutil.which(app_name + ".exe")
    if executable:
        try:
            subprocess.Popen(executable)
            return f"✅ Successfully launched {app_name} from system PATH."
        except Exception:
            pass
            
    return f"⚠️ Could not locate installed application '{app_name}' on this device."



def resolve_app_executable_path(app_name: str) -> str | None:
    """Resolve exact executable or shortcut path on C: or D: drives for common applications."""
    import shutil
    app_lower = app_name.lower().strip()
    target_name = APP_MAP.get(app_lower, app_lower)

    # 1. Prioritize Direct Hardcoded .exe Paths (prevents black cmd windows from opening)
    known_paths = {
        "code": [
            r"D:\Users\Arshad\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            r"C:\Users\Arshad\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
        "terminal": [
            r"C:\Users\Arshad\AppData\Local\Microsoft\WindowsApps\wt.exe",
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            r"C:\Windows\System32\cmd.exe",
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\Arshad\AppData\Local\Google\Chrome\Application\chrome.exe",
        ],
        "brave": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"D:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
    }

    for key, paths in known_paths.items():
        if key in app_lower or app_lower in key or target_name.lower().startswith(key):
            for p in paths:
                if os.path.exists(p):
                    return p

    # 2. System PATH lookup (.exe first, then .cmd)
    which_path = shutil.which(target_name) or shutil.which(app_lower)
    if which_path and os.path.exists(which_path):
        return which_path

    which_cmd = shutil.which(target_name.replace(".exe", ".cmd"))
    if which_cmd and os.path.exists(which_cmd):
        return which_cmd

    return None


def open_app(app_name: str) -> str:
    """Resolve and open target using ResourceResolverManager (URLs, Apps, Files, Folders, Settings)."""
    from brain.resolvers.manager import ResourceResolverManager
    from brain.resolvers.base import ResourceType
    from brain.tools.launcher import launch_application
    from brain.knowledge.graph import add_knowledge_edge

    app_lower = app_name.lower().strip()
    log_agent_action("OSAgent", f"Requested to open target: '{app_name}'")

    manager = ResourceResolverManager()
    resolved = manager.classify_and_resolve(app_name)

    res_type = resolved.get("resource_type")
    res_target = resolved.get("resolved_target")

    # 1. URL Resource
    if res_type == ResourceType.URL and res_target:
        browser_tag = resolved.get("metadata", {}).get("browser")
        if browser_tag:
            browser_exe = resolve_app_executable_path(browser_tag)
            if browser_exe:
                try:
                    subprocess.Popen([browser_exe, res_target])
                    msg = f"Opened URL {res_target} in {browser_tag.title()} ({browser_exe})"
                    log_agent_action("OSAgent", msg)
                    try:
                        add_knowledge_edge("User", "User", "OPENED_URL", res_target, "URL")
                    except Exception:
                        pass
                    return msg
                except Exception:
                    pass

        try:
            webbrowser.open(res_target)
            msg = f"Opened URL in default browser: {res_target}"
            log_agent_action("OSAgent", msg)
            try:
                add_knowledge_edge("User", "User", "OPENED_URL", res_target, "URL")
            except Exception:
                pass
            return msg
        except Exception as e:
            return f"❌ Failed to open URL {res_target}: {e}"

    # 2. Application Resource
    if res_type == ResourceType.APPLICATION and res_target:
        app_name_display = resolved.get("metadata", {}).get("app_name", app_name)
        res = launch_application(res_target, app_name_display)
        try:
            add_knowledge_edge("User", "User", "OPENED_APP", app_name_display, "Application")
        except Exception:
            pass
        return res

    # 3. Settings Resource
    if res_type == ResourceType.SETTINGS and res_target:
        try:
            subprocess.Popen(["explorer.exe", res_target])
            msg = f"✅ Opened settings: {res_target}"
            log_agent_action("OSAgent", msg)
            try:
                add_knowledge_edge("User", "User", "OPENED_SETTINGS", res_target, "Settings")
            except Exception:
                pass
            return msg
        except Exception as e:
            return f"❌ Failed to open settings {res_target}: {e}"

    # 4. Folder Resource
    if res_type == ResourceType.FOLDER and res_target:
        try:
            subprocess.Popen(["explorer.exe", os.path.abspath(res_target)])
            msg = f"✅ Opened folder: {res_target}"
            log_agent_action("OSAgent", msg)
            try:
                add_knowledge_edge("User", "User", "OPENED_FOLDER", res_target, "Folder")
            except Exception:
                pass
            return msg
        except Exception as e:
            return f"❌ Failed to open folder {res_target}: {e}"

    # 5. File Resource
    if res_type == ResourceType.FILE and res_target:
        ext = os.path.splitext(res_target)[1].lower()
        if ext in (".db", ".sqlite", ".sqlite3"):
            code_exe = r"D:\Users\Arshad\AppData\Local\Programs\Microsoft VS Code\Code.exe"
            if os.path.exists(code_exe):
                subprocess.Popen([code_exe, res_target])
                return f"✅ '{os.path.basename(res_target)}' is a SQLite database. Opened safely in Visual Studio Code: {res_target}"
            else:
                return f"ℹ️ '{os.path.basename(res_target)}' is a SQLite database file at: {res_target}. Open with DB Browser for SQLite or VS Code."

        try:
            if hasattr(os, "startfile"):
                os.startfile(res_target)
            else:
                subprocess.Popen([res_target])
            msg = f"✅ Opened file: {res_target}"
            log_agent_action("OSAgent", msg)
            try:
                add_knowledge_edge("User", "User", "OPENED_FILE", res_target, "File")
            except Exception:
                pass
            return msg
        except Exception as e:
            # Fallback to VS Code or Notepad for unassociated binary/text files (WinError 1155)
            try:
                code_exe = r"D:\Users\Arshad\AppData\Local\Programs\Microsoft VS Code\Code.exe"
                if os.path.exists(code_exe):
                    subprocess.Popen([code_exe, res_target])
                    return f"✅ Opened file in Visual Studio Code: {res_target}"
                else:
                    subprocess.Popen(["notepad.exe", res_target])
                    return f"✅ Opened file in Notepad: {res_target}"
            except Exception:
                return f"❌ Failed to open file {res_target}: {e}"

    # Legacy Fallback for direct URLs
    if app_lower.startswith("http://") or app_lower.startswith("https://") or "localhost" in app_lower:
        url = app_name if app_lower.startswith(("http://", "https://")) else f"http://{app_name}"
        try:
            webbrowser.open(url)
            return f"Opened URL in default browser: {url}"
        except Exception as e:
            return f"❌ Failed to open URL: {e}"

    return f"❌ [OSAgent Error] Application or resource '{app_name}' is not installed or could not be opened."

    # Executable path resolver fallback across C: and D: drives
    target_path = resolve_app_executable_path(app_name)
    if target_path and os.path.exists(target_path):
        res = launch_application(target_path, app_name)
        add_knowledge_edge("User", "User", "OPENED", app_name, "Application")
        return res

    # Fallback registry and Start Menu search
    dynamic_res = find_and_open_installed_app(app_name)
    if "Successfully" in dynamic_res:
        log_agent_action("OSAgent", dynamic_res)
        return dynamic_res

    err = f"❌ [OSAgent Error] Application '{app_name}' is not installed or could not be opened."
    log_agent_action("OSAgent", err)
    return err


def gui_type_and_enter(text: str) -> str:
    """Simulate typing text and pressing enter using PyAutoGUI."""
    if not PYAUTOGUI_AVAILABLE:
        return "⚠️ PyAutoGUI package is not installed or available on this system."
        
    log_agent_action("OSAgent", f"GUI Automation: Typing '{text[:30]}...' and Enter")
    try:
        pyautogui.write(text, interval=0.05)
        pyautogui.press('enter')
        return "Type and Enter simulated successfully."
    except Exception as e:
        return f"❌ PyAutoGUI action failed: {e}"


def gui_press_key(key: str) -> str:
    """Simulate pressing a specific keyboard key."""
    if not PYAUTOGUI_AVAILABLE:
        return "⚠️ PyAutoGUI package is not installed."
        
    log_agent_action("OSAgent", f"GUI Automation: Pressing key '{key}'")
    try:
        pyautogui.press(key)
        return f"Key '{key}' pressed successfully."
    except Exception as e:
        return f"❌ PyAutoGUI key press failed: {e}"


def safe_write_file(filepath: str, content: str, open_after: bool = False) -> str:
    """Create a text file with content in a safe directory and optionally open it in Notepad."""
    from pathlib import Path
    log_agent_action("OSAgent", f"Request to write file: {filepath}")
    
    # Resolve absolute path
    path_obj = Path(filepath).resolve()
    
    # Enforce safe directory: Must be under D:/Noor or user profile
    allowed_root = Path("D:/Noor").resolve()
    allowed_user = Path("C:/Users/Arshad").resolve()
    
    is_in_noor = str(path_obj).startswith(str(allowed_root))
    is_in_user = str(path_obj).startswith(str(allowed_user))
    
    if not (is_in_noor or is_in_user):
        # Default to saving in D:/Noor/data/ if path is not absolute or unsafe
        filename = path_obj.name
        path_obj = (allowed_root / "data" / filename).resolve()
        
    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(content, encoding="utf-8")
        
        # Verify writing (Rule 3)
        if not path_obj.exists():
            err = f"❌ Tool Verification Failure: File was not created at: {path_obj}"
            log_agent_action("OSAgent", err)
            return err
        if path_obj.stat().st_size == 0 and len(content) > 0:
            err = f"❌ Tool Verification Failure: Created file at {path_obj} is empty."
            log_agent_action("OSAgent", err)
            return err
            
        msg = f"✅ File created successfully at: {path_obj}"
        
        if open_after:
            subprocess.Popen(["notepad.exe", str(path_obj)])
            msg += "\nOpened file in Notepad."
            
        log_agent_action("OSAgent", msg)
        return msg
    except Exception as e:
        err = f"❌ Failed to write file: {e}"
        log_agent_action("OSAgent", err)
        return err


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1.2 — Windows Desktop Awareness & Controls (Zero-Dependency)
# ─────────────────────────────────────────────────────────────────────────────

from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# Configure ctypes functions for 64-bit Windows compatibility
user32.OpenClipboard.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [wintypes.HWND]

user32.CloseClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []

user32.EmptyClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []

user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]

user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

# Global Memory functions
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]

kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]

kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]

# Window and Process functions
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []

user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]

user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]

user32.IsIconic.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]

user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]


def get_focused_app_and_title() -> dict:
    """Get the name and title of the currently focused window using ctypes."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"title": "No active window", "app": "Unknown"}
            
        # Get window title
        length = user32.GetWindowTextLengthW(hwnd)
        title = "Unnamed Window"
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            
        # Get process ID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        # Open process to query name
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        app_name = "Unknown"
        if h_process:
            size = wintypes.DWORD(260)
            buf = ctypes.create_unicode_buffer(260)
            if kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                app_path = buf.value
                app_name = os.path.basename(app_path)
            kernel32.CloseHandle(h_process)
            
        return {"title": title, "app": app_name}
    except Exception as e:
        return {"title": f"Error: {e}", "app": "Unknown"}


def get_active_window_title() -> str:
    """Get a descriptive string of the active window and its executable name."""
    info = get_focused_app_and_title()
    title = info["title"]
    app = info["app"]
    if app != "Unknown":
        return f"{title} ({app})"
    return title


def get_clipboard_text() -> str:
    """Retrieve unicode text contents from the Windows clipboard with retries."""
    import time
    for _ in range(5):
        try:
            if user32.OpenClipboard(None):
                h_clip_mem = user32.GetClipboardData(CF_UNICODETEXT)
                text = ""
                if h_clip_mem:
                    lp_str = kernel32.GlobalLock(h_clip_mem)
                    if lp_str:
                        text = ctypes.c_wchar_p(lp_str).value
                        kernel32.GlobalUnlock(h_clip_mem)
                user32.CloseClipboard()
                return text or ""
        except Exception as e:
            try:
                user32.CloseClipboard()
            except:
                pass
        time.sleep(0.1)
    return "Clipboard is empty or contains non-text content."


def set_clipboard_text(text: str) -> bool:
    """Copy a unicode string to the Windows clipboard with retries."""
    import time
    for _ in range(5):
        try:
            if user32.OpenClipboard(None):
                user32.EmptyClipboard()
                # Encode as UTF-16 Little Endian (unicode format for CF_UNICODETEXT)
                text_bytes = (text + '\0').encode('utf-16le')
                h_global_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
                if h_global_mem:
                    lp_str = kernel32.GlobalLock(h_global_mem)
                    if lp_str:
                        ctypes.memmove(lp_str, text_bytes, len(text_bytes))
                        kernel32.GlobalUnlock(h_global_mem)
                        user32.SetClipboardData(CF_UNICODETEXT, h_global_mem)
                user32.CloseClipboard()
                return True
        except Exception:
            try:
                user32.CloseClipboard()
            except:
                pass
        time.sleep(0.1)
    return False


def switch_to_window(title_substring: str) -> str:
    """Search visible windows and switch the first matching window to the foreground."""
    target_lower = title_substring.lower().strip()
    log_agent_action("OSAgent", f"Switching to window matching: '{title_substring}'")
    
    found_hwnds = []
    
    def enum_windows_callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if target_lower in title.lower():
                    found_hwnds.append((hwnd, title))
        return True
        
    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    
    if not found_hwnds:
        return f"⚠️ No open window found matching '{title_substring}'."
        
    hwnd, title = found_hwnds[0]
    
    # Restore if minimized
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    else:
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
        
    user32.SetForegroundWindow(hwnd)
    
    msg = f"✅ Switched to window: '{title}'"
    log_agent_action("OSAgent", msg)
    return msg


def close_whitelisted_app(app_name: str) -> str:
    """Safely close a running application matching the whitelist."""
    app_lower = app_name.lower().strip()
    log_agent_action("OSAgent", f"Requested to close application: '{app_name}'")
    
    # Resolve mapped exe
    exe_name = APP_MAP.get(app_lower)
    if not exe_name:
        # Also check if it's already an exe name that is in the whitelist values
        allowed_exes = set(APP_MAP.values())
        if app_lower in allowed_exes:
            exe_name = app_lower
        elif app_lower + ".exe" in allowed_exes:
            exe_name = app_lower + ".exe"
            
    if not exe_name:
        return f"⚠️ [OSAgent Security] Application '{app_name}' is not in the safe whitelist."
        
    try:
        # Run taskkill safely
        res = subprocess.run(
            ["taskkill", "/F", "/IM", exe_name],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        
        if res.returncode == 0:
            msg = f"✅ Successfully closed application: {exe_name}"
        else:
            if "not found" in res.stderr.lower() or "not found" in res.stdout.lower():
                msg = f"ℹ️ Application '{exe_name}' is already closed (not running)."
            else:
                msg = f"⚠️ Close process '{exe_name}' returned code {res.returncode}. Output: {res.stdout.strip()} {res.stderr.strip()}"
            
        log_agent_action("OSAgent", msg)
        return msg
    except Exception as e:
        err = f"❌ Failed to close {exe_name}: {e}"
        log_agent_action("OSAgent", err)
        return err


def show_desktop_notification(title: str, message: str) -> str:
    """Display a Windows desktop notification toast using a native PowerShell script."""
    log_agent_action("OSAgent", f"Showing desktop notification: '{title}' - '{message}'")
    
    t_escaped = title.replace("'", "''")
    m_escaped = message.replace("'", "''")
    
    ps_cmd = (
        f"[void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
        f"$notification = New-Object System.Windows.Forms.NotifyIcon; "
        f"$notification.Icon = [System.Drawing.SystemIcons]::Information; "
        f"$notification.BalloonTipIcon = 'Info'; "
        f"$notification.BalloonTipTitle = '{t_escaped}'; "
        f"$notification.BalloonTipText = '{m_escaped}'; "
        f"$notification.Visible = $true; "
        f"$notification.ShowBalloonTip(5000); "
        f"Start-Sleep -s 1; "
        f"$notification.Dispose()"
    )
    
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return "✅ Notification trigger sent."
    except Exception as e:
        err = f"❌ Failed to trigger notification: {e}"
        log_agent_action("OSAgent", err)
        return err


def get_disk_space() -> str:
    """Retrieve free and total disk space for all logical drives."""
    import shutil
    log_agent_action("OSAgent", "Checking disk space...")
    try:
        # On Windows, we can check standard drives (C:, D:, etc.)
        drives = []
        for letter in ["C", "D", "E", "F"]:
            path = f"{letter}:\\"
            if os.path.exists(path):
                try:
                    total, used, free = shutil.disk_usage(path)
                    # Convert to GB
                    total_gb = total / (1024**3)
                    free_gb = free / (1024**3)
                    used_gb = used / (1024**3)
                    drives.append(
                        f"Drive {letter}:\\ -> {free_gb:.1f} GB free of {total_gb:.1f} GB ({used_gb:.1f} GB used)"
                    )
                except Exception:
                    pass
        if not drives:
            # Fallback to current directory drive
            total, used, free = shutil.disk_usage(".")
            total_gb = total / (1024**3)
            free_gb = free / (1024**3)
            drives.append(f"Current Drive -> {free_gb:.1f} GB free of {total_gb:.1f} GB")
            
        res = "\n".join(drives)
        log_agent_action("OSAgent", "Disk space checked successfully.", res)
        return res
    except Exception as e:
        err = f"❌ Failed to retrieve disk space: {e}"
        log_agent_action("OSAgent", err)
        return err


def _read_pdf_content(filepath: Path) -> str:
    """Helper to extract text from a PDF file using pypdf/PyPDF2, falling back to raw extraction."""
    from brain.memory import log_agent_action
    
    # 1. Try pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(filepath)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        if text.strip():
            log_agent_action("OSAgent", "Successfully extracted PDF text using pypdf.")
            return text.strip()
    except ImportError:
        pass
    except Exception as e:
        log_agent_action("OSAgent", f"pypdf extraction failed: {e}")

    # 2. Try PyPDF2
    try:
        import PyPDF2
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            if text.strip():
                log_agent_action("OSAgent", "Successfully extracted PDF text using PyPDF2.")
                return text.strip()
    except ImportError:
        pass
    except Exception as e:
        log_agent_action("OSAgent", f"PyPDF2 extraction failed: {e}")

    # 3. Fallback to raw binary regex scanning
    try:
        log_agent_action("OSAgent", "Falling back to raw binary search for PDF content.")
        with open(filepath, 'rb') as f:
            content = f.read()
        import re
        # PDF string literals are enclosed in parentheses: (string)
        # Match bytes inside parentheses while ignoring escaped ones
        matches = re.findall(b'(?<!\\\\)\\((.*?)(?<!\\\\)\\)', content)
        extracted = []
        for m in matches:
            try:
                # Decode bytes and strip non-printable characters
                text_part = m.decode('utf-8', errors='ignore')
                clean_part = "".join(c for c in text_part if c.isprintable() or c in "\r\n\t")
                if len(clean_part.strip()) > 1:
                    extracted.append(clean_part)
            except Exception:
                pass
        raw_text = " ".join(extracted)
        raw_text = re.sub(r'\s+', ' ', raw_text).strip()
        if raw_text:
            return raw_text
        return "⚠️ PDF file is empty or contains no extractable text."
    except Exception as e:
        return f"❌ Failed to extract PDF content: {e}"


def safe_read_file(filepath: str) -> str:
    """Safely read and return the contents of a text or PDF file."""
    from pathlib import Path
    log_agent_action("OSAgent", f"Request to read file: {filepath}")
    path_obj = Path(filepath).resolve()
    
    # Enforce safe directory: Must be under D:/Noor or user profile
    allowed_root = Path("D:/Noor").resolve()
    allowed_user = Path("C:/Users/Arshad").resolve()
    
    is_in_noor = str(path_obj).startswith(str(allowed_root))
    is_in_user = str(path_obj).startswith(str(allowed_user))
    
    if not (is_in_noor or is_in_user):
        return f"⚠️ [OSAgent Security] Access denied: File must be under D:/Noor or C:/Users/Arshad."
        
    if not path_obj.exists():
        return f"⚠️ File does not exist: {filepath}"
        
    # Check for PDF extension
    if path_obj.suffix.lower() == ".pdf":
        return _read_pdf_content(path_obj)
        
    try:
        return path_obj.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Failed to read file: {e}"


def search_local_files(name_query: str) -> str:
    """
    Search recursively inside Desktop, Downloads, Documents, and D:/Noor
    for files matching the input keyword in their name (case-insensitive).
    Limit matches to 15 items.
    """
    from pathlib import Path
    log_agent_action("OSAgent", f"Searching local files for query: '{name_query}'")
    
    search_dirs = [
        Path("C:/Users/Arshad/Desktop"),
        Path("C:/Users/Arshad/Downloads"),
        Path("C:/Users/Arshad/Documents"),
        Path("D:/Noor")
    ]
    
    query_lower = name_query.lower().strip()
    matches = []
    
    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        try:
            exclude_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", ".agents", ".gemini"}
            
            for root, dirs, files in os.walk(base_dir):
                # Modify dirs in-place to prune excluded folders
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if query_lower in file.lower():
                        full_path = os.path.join(root, file)
                        matches.append(full_path)
                        if len(matches) >= 15:
                            break
                if len(matches) >= 15:
                    break
        except Exception as e:
            log_agent_action("OSAgent", f"Failed to search in {base_dir}: {e}")
        if len(matches) >= 15:
            break
            
    if not matches:
        return f"🔍 No files found matching '{name_query}' in Desktop, Downloads, Documents, or D:/Noor."
        
    res = f"🔍 Found {len(matches)} matching files:\n"
    for m in matches:
        res += f"  📄 {m}\n"
    return res



def safe_edit_file(filepath: str, new_content: str, append: bool = False) -> str:
    """Safely edit a file by either appending or overwriting it."""
    from pathlib import Path
    log_agent_action("OSAgent", f"Request to edit file (append={append}): {filepath}")
    path_obj = Path(filepath).resolve()
    
    allowed_root = Path("D:/Noor").resolve()
    allowed_user = Path("C:/Users/Arshad").resolve()
    
    is_in_noor = str(path_obj).startswith(str(allowed_root))
    is_in_user = str(path_obj).startswith(str(allowed_user))
    
    if not (is_in_noor or is_in_user):
        return f"⚠️ [OSAgent Security] Access denied: File must be under D:/Noor or C:/Users/Arshad."
        
    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if append:
            with open(path_obj, "a", encoding="utf-8") as f:
                f.write(new_content)
            # Verify edits (Rule 3)
            edited_text = path_obj.read_text(encoding="utf-8", errors="replace")
            if new_content not in edited_text:
                return f"❌ Tool Verification Failure: Appended content could not be verified in: {filepath}"
            return f"✅ Content appended to file: {filepath}"
        else:
            path_obj.write_text(new_content, encoding="utf-8")
            # Verify edits (Rule 3)
            edited_text = path_obj.read_text(encoding="utf-8", errors="replace")
            if new_content not in edited_text:
                return f"❌ Tool Verification Failure: Overwritten content could not be verified in: {filepath}"
            return f"✅ File overwritten successfully: {filepath}"
    except Exception as e:
        return f"❌ Failed to edit file: {e}"


def safe_delete_file(filepath: str, confirmed: bool = False) -> str:
    """Safely delete a file, requiring explicit confirmation."""
    from pathlib import Path
    log_agent_action("OSAgent", f"Request to delete file (confirmed={confirmed}): {filepath}")
    path_obj = Path(filepath).resolve()
    
    allowed_root = Path("D:/Noor").resolve()
    allowed_user = Path("C:/Users/Arshad").resolve()
    
    is_in_noor = str(path_obj).startswith(str(allowed_root))
    is_in_user = str(path_obj).startswith(str(allowed_user))
    
    if not (is_in_noor or is_in_user):
        return f"⚠️ [OSAgent Security] Access denied: File must be under D:/Noor or C:/Users/Arshad."
        
    if not path_obj.exists():
        return f"⚠️ File does not exist: {filepath}"
        
    if not confirmed:
        return f"⚠️ CONFIRMATION REQUIRED: Please explicitly confirm that you want to delete {filepath}."
        
    try:
        path_obj.unlink()
        # Verify deletion (Rule 3)
        if path_obj.exists():
            return f"❌ Tool Verification Failure: File was not deleted at: {filepath}"
        return f"✅ File deleted successfully: {filepath}"
    except Exception as e:
        return f"❌ Failed to delete file: {e}"


def set_radio_state(radio_kind: str, state: str) -> str:
    """Toggle Radio state ('On' or 'Off') for 'Bluetooth' or 'WiFi' using PowerShell WinRT API."""
    log_agent_action("OSAgent", f"Setting radio state: {radio_kind} -> {state}")
    ps_cmd = (
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]; "
        "Function Await($WinRtTask, $ResultType) { "
        "    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType); "
        "    $netTask = $asTask.Invoke($null, @($WinRtTask)); "
        "    $netTask.Wait(-1) | Out-Null; "
        "    $netTask.Result "
        "}; "
        "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
        "$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]); "
        f"$radio = $radios | ? {{ $_.Kind -eq '{radio_kind}' }}; "
        "if ($radio) { "
        f"    $res = Await ($radio.SetStateAsync('{state}')) ([Windows.Devices.Radios.RadioAccessStatus]); "
        "    echo \"SUCCESS: $res\" "
        "} else { "
        "    echo 'NO_DEVICE' "
        "}"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=8.0
        )
        out = res.stdout.strip()
        if "SUCCESS" in out:
            if "Allowed" in out:
                return f"✅ Successfully turned {state.lower()} {radio_kind}."
            else:
                return f"⚠️ Changing {radio_kind} state returned status: {out}."
        elif "NO_DEVICE" in out:
            return f"⚠️ No {radio_kind} radio hardware found on this system."
        else:
            return f"❌ Failed to toggle {radio_kind}: {out} {res.stderr.strip()}"
    except Exception as e:
        err = f"❌ Failed to set radio state: {e}"
        log_agent_action("OSAgent", err)
        return err


def toggle_airplane_mode(state: str) -> str:
    """Simulate Airplane Mode by turning Off or On both WiFi and Bluetooth radios."""
    log_agent_action("OSAgent", f"Toggling airplane mode: {state}")
    
    wifi_state = "Off" if state == "On" else "On"
    bt_state = "Off" if state == "On" else "On"
    
    res_wifi = set_radio_state("WiFi", wifi_state)
    res_bt = set_radio_state("Bluetooth", bt_state)
    
    status = []
    if "Successfully" in res_wifi:
        status.append(f"Wi-Fi turned {wifi_state.lower()}")
    else:
        status.append(f"Wi-Fi: {res_wifi}")
        
    if "Successfully" in res_bt:
        status.append(f"Bluetooth turned {bt_state.lower()}")
    else:
        status.append(f"Bluetooth: {res_bt}")
        
    mode_str = "enabled" if state == "On" else "disabled"
    return f"✅ Airplane mode {mode_str} ({', '.join(status)})."


def get_dir_list(path: str) -> str:
    """List directory contents and count files/folders safely."""
    from pathlib import Path
    
    # Resolve aliases using FOLDER_MAP
    path_clean = path.lower().strip().replace('"', '').replace("'", "")
    if path_clean in FOLDER_MAP:
        path = FOLDER_MAP[path_clean]
        
    log_agent_action("OSAgent", f"Listing directory: {path}")
    
    # Enforce safe directories (Downloads, Desktop, documents, D:/Noor, C:/Users/Arshad, D:/Users/Arshad)
    allowed_root = Path("D:/Noor").resolve()
    allowed_user_c = Path("C:/Users/Arshad").resolve()
    allowed_user_d = Path("D:/Users/Arshad").resolve()
    
    try:
        path_obj = Path(path).resolve()
        
        is_in_noor = str(path_obj).startswith(str(allowed_root))
        is_in_user_c = str(path_obj).startswith(str(allowed_user_c))
        is_in_user_d = str(path_obj).startswith(str(allowed_user_d))
        
        if not (is_in_noor or is_in_user_c or is_in_user_d):
            return f"⚠️ [OSAgent Security] Access denied: Folder must be under D:/Noor or user directories."
            
        if not path_obj.exists():
            return f"⚠️ Directory does not exist: {path}"
        if not path_obj.is_dir():
            return f"⚠️ Path is not a directory: {path}"
            
        items = list(path_obj.iterdir())
        files = [i for i in items if i.is_file()]
        dirs = [i for i in items if i.is_dir()]
        
        summary = f"📁 Directory: {path_obj}\n"
        summary += f"📊 Total items: {len(items)} ({len(files)} files, {len(dirs)} folders)\n\n"
        
        if items:
            summary += "Contents:\n"
            # Sort items: directories first, then files
            sorted_items = sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in sorted_items[:30]:
                icon = "📁" if item.is_dir() else "📄"
                summary += f"  {icon} {item.name}\n"
            if len(items) > 30:
                summary += f"  ... and {len(items) - 30} more items.\n"
        else:
            summary += "Folder is empty."
            
        return summary
    except Exception as e:
        return f"❌ Failed to list directory: {e}"

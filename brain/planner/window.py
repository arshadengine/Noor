"""
brain/planner/window.py
─────────────────────────────────────────────────────
Foreground Window Focus Manager for Windows OS.
Uses Win32 user32 API via 64-bit safe ctypes to restore and bring application windows directly into focus.
"""

import ctypes
import os
import psutil
from typing import Optional, Tuple


def get_window_handle_for_process(process_name_or_pid) -> Tuple[int, str]:
    """Find main top-level window handle (HWND) and title for process name or PID."""
    if os.name != 'nt':
        return 0, ""

    user32 = ctypes.windll.user32
    target_pids = set()

    if isinstance(process_name_or_pid, int):
        target_pids.add(process_name_or_pid)
    elif isinstance(process_name_or_pid, str):
        p_name = process_name_or_pid.lower()
        if not p_name.endswith(".exe"):
            p_name += ".exe"
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == p_name:
                    target_pids.add(proc.info['pid'])
        except Exception:
            pass

    if not target_pids:
        return 0, ""

    found_hwnd = 0
    found_title = ""

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_size_t, ctypes.c_size_t)
    user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_size_t]

    def enum_windows_callback(hwnd, lparam):
        nonlocal found_hwnd, found_title
        if not user32.IsWindowVisible(hwnd):
            return 1

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        if pid.value in target_pids:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                if title and not title.startswith("MSCTFIME") and not title.startswith("Default IME"):
                    found_hwnd = hwnd
                    found_title = title
                    return 0
        return 1

    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    return found_hwnd, found_title


def bring_window_to_foreground(process_name_or_pid, window_title: Optional[str] = None) -> bool:
    """
    Bring a process's main window directly into active foreground focus.
    Restores minimized windows and calls SetForegroundWindow.
    """
    if os.name != 'nt':
        return False

    hwnd, title = get_window_handle_for_process(process_name_or_pid)
    if not hwnd:
        return False

    try:
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print(f"[WindowManager Note] Foreground focus exception: {e}")
        return False

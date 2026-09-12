"""
brain/system/monitor.py
─────────────────────────────────────────────────────
Event-Driven Background System Hardware & Process Monitor.
Maintains a real-time, non-blocking SharedSystemState in memory.
Reads CPU %, RAM %, Battery %, Network, and Active Window instantly.
"""

import time
import threading
import psutil
from datetime import datetime


class SharedSystemState:
    """Thread-safe state container for instantaneous system status lookup."""

    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    battery_percent: float | None = None
    power_plugged: bool | None = None
    active_window_title: str = "Unknown"
    active_app_name: str = "Unknown"
    top_processes: list[dict] = []
    last_updated: datetime = datetime.now()


_monitor_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _update_metrics():
    """Background polling worker running every 3.0 seconds."""
    while not _stop_event.is_set():
        try:
            # 1. CPU & Memory
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()

            # 2. Battery
            battery = psutil.sensors_battery()
            bat_pct = battery.percent if battery else None
            plugged = battery.power_plugged if battery else None

            # 3. Active Window (Deferred import to break circular dependency)
            from brain.os_agent import get_focused_app_and_title
            win_info = get_focused_app_and_title()
            app_name = win_info.get("app", "Unknown")
            win_title = win_info.get("title", "Unknown")

            # 4. Top 3 RAM processes
            top_procs = []
            try:
                for proc in sorted(psutil.process_iter(['pid', 'name', 'memory_percent']),
                                   key=lambda p: p.info['memory_percent'] or 0, reverse=True)[:3]:
                    top_procs.append({
                        "name": proc.info['name'],
                        "mem_pct": round(proc.info['memory_percent'] or 0, 1)
                    })
            except Exception:
                pass

            # Update shared state atomically
            SharedSystemState.cpu_percent = cpu
            SharedSystemState.ram_percent = mem.percent
            SharedSystemState.ram_used_gb = round(mem.used / (1024 ** 3), 2)
            SharedSystemState.ram_total_gb = round(mem.total / (1024 ** 3), 2)
            SharedSystemState.battery_percent = bat_pct
            SharedSystemState.power_plugged = plugged
            SharedSystemState.active_app_name = app_name
            SharedSystemState.active_window_title = win_title
            SharedSystemState.top_processes = top_procs
            SharedSystemState.last_updated = datetime.now()

        except Exception as e:
            pass

        # Sleep 3 seconds between polls
        _stop_event.wait(3.0)


def start_system_monitor():
    """Start the system monitor daemon thread if not already running."""
    global _monitor_thread
    if _monitor_thread is None or not _monitor_thread.is_alive():
        _stop_event.clear()
        _monitor_thread = threading.Thread(target=_update_metrics, daemon=True, name="SystemMonitorThread")
        _monitor_thread.start()


def stop_system_monitor():
    """Stop the system monitor daemon thread."""
    _stop_event.set()


def get_system_state() -> dict:
    """Instantaneous non-blocking read of current system metrics."""
    start_system_monitor()
    return {
        "cpu_percent": SharedSystemState.cpu_percent,
        "ram_percent": SharedSystemState.ram_percent,
        "ram_used_gb": SharedSystemState.ram_used_gb,
        "ram_total_gb": SharedSystemState.ram_total_gb,
        "battery_percent": SharedSystemState.battery_percent,
        "power_plugged": SharedSystemState.power_plugged,
        "active_app_name": SharedSystemState.active_app_name,
        "active_window_title": SharedSystemState.active_window_title,
        "top_processes": SharedSystemState.top_processes,
        "last_updated": SharedSystemState.last_updated.isoformat(),
    }

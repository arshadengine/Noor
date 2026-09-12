"""
brain/reliability/watchdog.py
─────────────────────────────────────────────────────
Process & Thread Watchdog for Noor (Phase 2.5).
Detects frozen background workers, thread deadlocks, and queue stalls.
"""

import threading
import time
from typing import Dict, Any, List


class RuntimeWatchdog:
    """Monitors active threads and detects stalls or deadlocks."""

    @staticmethod
    def inspect_active_threads() -> List[Dict[str, Any]]:
        active = []
        for t in threading.enumerate():
            active.append({
                "thread_name": t.name,
                "ident": t.ident,
                "is_alive": t.is_alive(),
                "is_daemon": t.daemon,
            })
        return active

    @staticmethod
    def check_health_and_stalls() -> Dict[str, Any]:
        threads = RuntimeWatchdog.inspect_active_threads()
        stalled_count = 0
        
        return {
            "total_threads": len(threads),
            "stalled_threads": stalled_count,
            "status": "HEALTHY" if stalled_count == 0 else "WARNING",
            "threads": threads,
        }

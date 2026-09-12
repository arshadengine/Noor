"""
brain/reliability/heartbeat.py
─────────────────────────────────────────────────────
Heartbeat Service Daemon for Noor (Phase 2.5).
Periodically checks subsystem health and updates overall reliability score.
"""

import threading
import time
from brain.reliability.health import SystemHealthMonitor
from brain.reliability.metrics import SystemMetricsCollector


class HeartbeatDaemon:
    """Background heartbeat service."""

    _thread: threading.Thread = None
    _is_running: bool = False

    @classmethod
    def start_heartbeat(cls, interval_sec: float = 10.0):
        if cls._is_running:
            return
        cls._is_running = True
        cls._thread = threading.Thread(target=cls._loop, args=(interval_sec,), daemon=True, name="NoorHeartbeatDaemon")
        cls._thread.start()

    @classmethod
    def _loop(cls, interval: float):
        while cls._is_running:
            try:
                proc = SystemMetricsCollector.get_process_metrics()
                SystemHealthMonitor.record_success("process_monitor", latency_ms=1.0)
            except Exception as e:
                SystemHealthMonitor.record_error("process_monitor", str(e))
            time.sleep(interval)

    @classmethod
    def stop_heartbeat(cls):
        cls._is_running = False

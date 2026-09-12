"""
brain/reliability/metrics.py
─────────────────────────────────────────────────────
System Performance & Health Metrics Collector for Noor (Phase 2.5).
Tracks RAM usage, CPU %, latency distributions, queue depth, error rates, and recovery success.
"""

import os
import psutil
from typing import Dict, Any


class SystemMetricsCollector:
    """Collects real-time process and system hardware metrics."""

    @staticmethod
    def get_process_metrics() -> Dict[str, Any]:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        cpu_pct = process.cpu_percent(interval=0.01)

        return {
            "pid": os.getpid(),
            "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
            "vms_mb": round(mem_info.vms / (1024 * 1024), 2),
            "cpu_percent": cpu_pct,
            "num_threads": process.num_threads(),
        }

    @staticmethod
    def get_system_hardware_metrics() -> Dict[str, Any]:
        return {
            "system_cpu_percent": psutil.cpu_percent(interval=0.01),
            "system_ram_percent": psutil.virtual_memory().percent,
            "system_ram_available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
        }

"""
brain/reliability/diagnostics.py
─────────────────────────────────────────────────────
System Diagnostics & Structured Snapshot API for Noor (Phase 2.5).
Generates a single unified JSON snapshot aggregating overall reliability score and subsystem state.
"""

from typing import Dict, Any
from brain.reliability.health import SystemHealthMonitor
from brain.reliability.metrics import SystemMetricsCollector
from brain.reliability.watchdog import RuntimeWatchdog
from brain.reliability.profiler import MemoryProfiler
class SystemDiagnostics:
    """Generates comprehensive system diagnostics snapshots."""

    @staticmethod
    def get_system_diagnostics_snapshot() -> Dict[str, Any]:
        """
        Return a single unified JSON snapshot for control panel dashboards, telemetry, and debugging.
        Includes weighted overall_reliability_score (0-100%).
        """
        from brain.runtime import RuntimeInspector

        health_reports = SystemHealthMonitor.get_all_reports()
        overall_score = SystemHealthMonitor.get_overall_health_score()
        proc_metrics = SystemMetricsCollector.get_process_metrics()
        hw_metrics = SystemMetricsCollector.get_system_hardware_metrics()
        watchdog_status = RuntimeWatchdog.check_health_and_stalls()
        mem_growth = MemoryProfiler.detect_memory_growth()

        active_tasks = RuntimeInspector.get_active_tasks_summary()
        task_stats = {}

        return {
            "overall_reliability_score": overall_score,
            "system_health": health_reports,
            "active_tasks": active_tasks,
            "task_stats": task_stats,
            "process_metrics": proc_metrics,
            "hardware_metrics": hw_metrics,
            "watchdog": watchdog_status,
            "memory_profiler": mem_growth,
        }

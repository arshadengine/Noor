"""
brain/reliability/profiler.py
─────────────────────────────────────────────────────
Memory Profiler & Memory Leak Detector for Noor (Phase 2.5).
Tracks memory growth over extended runtime and detects leaks.
"""

from typing import Dict, Any, List
from brain.reliability.metrics import SystemMetricsCollector


class MemoryProfiler:
    """Tracks memory snapshots to detect leaks over time."""

    _snapshots: List[Dict[str, Any]] = []

    @classmethod
    def record_snapshot(cls, label: str = "checkpoint") -> Dict[str, Any]:
        metrics = SystemMetricsCollector.get_process_metrics()
        snapshot = {
            "label": label,
            "rss_mb": metrics["rss_mb"],
            "timestamp": metrics.get("timestamp", 0.0),
        }
        cls._snapshots.append(snapshot)
        return snapshot

    @classmethod
    def detect_memory_growth(cls) -> Dict[str, Any]:
        if len(cls._snapshots) < 2:
            return {"status": "INSUFFICIENT_DATA", "growth_mb": 0.0}

        initial_rss = cls._snapshots[0]["rss_mb"]
        current_rss = cls._snapshots[-1]["rss_mb"]
        growth = round(current_rss - initial_rss, 2)

        return {
            "status": "STABLE" if growth < 50.0 else "WARNING_GROWTH",
            "initial_rss_mb": initial_rss,
            "current_rss_mb": current_rss,
            "growth_mb": growth,
            "snapshot_count": len(cls._snapshots),
        }

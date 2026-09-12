"""
brain/runtime/metrics.py
─────────────────────────────────────────────────────
Task Execution Time Metrics for Noor Runtime.
Measures queue time, planning time, execution time, verification time, and total duration.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TaskMetrics:
    queue_time_sec: float = 0.0
    planning_time_sec: float = 0.0
    execution_time_sec: float = 0.0
    verification_time_sec: float = 0.0
    total_time_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_time_sec": self.queue_time_sec,
            "planning_time_sec": self.planning_time_sec,
            "execution_time_sec": self.execution_time_sec,
            "verification_time_sec": self.verification_time_sec,
            "total_time_sec": self.total_time_sec,
        }

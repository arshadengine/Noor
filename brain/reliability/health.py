"""
brain/reliability/health.py
─────────────────────────────────────────────────────
Subsystem Health Monitoring & Health Score Calculation for Noor (Phase 2.5).
Defines SubsystemHealth and SystemHealthMonitor.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional


class HealthStatus(Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class SubsystemHealth:
    name: str
    status: HealthStatus = HealthStatus.ONLINE
    latency_ms: float = 0.0
    memory_mb: float = 0.0
    error_count: int = 0
    version: str = "2.5.0"
    last_successful_op: str = field(default_factory=lambda: datetime.now().isoformat())
    health_score: float = 100.0

    def calculate_health_score(self) -> float:
        """Calculate weighted health score (0-100%)."""
        if self.status == HealthStatus.OFFLINE:
            self.health_score = 0.0
            return 0.0
        
        penalty = min(self.error_count * 5.0, 50.0)
        if self.latency_ms > 1000.0:
            penalty += 20.0
        elif self.latency_ms > 500.0:
            penalty += 10.0

        if self.status == HealthStatus.DEGRADED:
            penalty += 25.0

        self.health_score = max(round(100.0 - penalty, 1), 0.0)
        return self.health_score

    def to_dict(self) -> Dict[str, Any]:
        self.calculate_health_score()
        return {
            "name": self.name,
            "status": self.status.value if isinstance(self.status, HealthStatus) else str(self.status),
            "latency_ms": self.latency_ms,
            "memory_mb": self.memory_mb,
            "error_count": self.error_count,
            "version": self.version,
            "last_successful_op": self.last_successful_op,
            "health_score": self.health_score,
        }


class SystemHealthMonitor:
    """Central Health Monitor for Noor Subsystems."""

    _subsystems: Dict[str, SubsystemHealth] = {}

    @classmethod
    def register_subsystem(cls, name: str, version: str = "2.5.0") -> SubsystemHealth:
        health = SubsystemHealth(name=name, version=version)
        cls._subsystems[name.lower()] = health
        return health

    @classmethod
    def record_success(cls, name: str, latency_ms: float = 0.0):
        key = name.lower()
        if key not in cls._subsystems:
            cls.register_subsystem(name)
        h = cls._subsystems[key]
        h.status = HealthStatus.ONLINE
        h.latency_ms = latency_ms
        h.last_successful_op = datetime.now().isoformat()
        h.calculate_health_score()

    @classmethod
    def record_error(cls, name: str, err_msg: str = ""):
        key = name.lower()
        if key not in cls._subsystems:
            cls.register_subsystem(name)
        h = cls._subsystems[key]
        h.error_count += 1
        if h.error_count >= 5:
            h.status = HealthStatus.OFFLINE
        elif h.error_count >= 2:
            h.status = HealthStatus.DEGRADED
        h.calculate_health_score()

    @classmethod
    def get_all_reports(cls) -> Dict[str, Dict[str, Any]]:
        return {name: h.to_dict() for name, h in cls._subsystems.items()}

    @classmethod
    def get_overall_health_score(cls) -> float:
        if not cls._subsystems:
            return 100.0
        scores = [h.calculate_health_score() for h in cls._subsystems.values()]
        return round(sum(scores) / len(scores), 1)

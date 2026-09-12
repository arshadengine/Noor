"""
brain/health.py
─────────────────────────────────────────────────────
Runtime Provider Health & Latency Monitor for Noor.

Tracks real-time status (Online, Busy, Rate Limited, Offline),
rolling average latency, success rates, and consecutive failure counts.
"""

from __future__ import annotations
import time
from typing import Any

class HealthMonitor:
    _instance: HealthMonitor | None = None

    def __new__(cls) -> HealthMonitor:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_monitor()
        return cls._instance

    def _init_monitor(self) -> None:
        self.providers: dict[str, dict[str, Any]] = {
            "gemini": {
                "status": "ONLINE",
                "latencies": [],
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_error": None,
                "last_success_time": time.time(),
            },
            "groq": {
                "status": "ONLINE",
                "latencies": [],
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_error": None,
                "last_success_time": time.time(),
            },
            "openrouter": {
                "status": "ONLINE",
                "latencies": [],
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_error": None,
                "last_success_time": time.time(),
            },
            "ollama": {
                "status": "ONLINE",
                "latencies": [],
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_error": None,
                "last_success_time": time.time(),
            },
        }

    def record_success(self, provider: str, latency_ms: float) -> None:
        if provider not in self.providers:
            return
        p = self.providers[provider]
        p["status"] = "ONLINE"
        p["success_count"] += 1
        p["consecutive_failures"] = 0
        p["last_success_time"] = time.time()
        
        # Keep rolling window of last 20 latencies
        p["latencies"].append(latency_ms)
        if len(p["latencies"]) > 20:
            p["latencies"].pop(0)

    def record_failure(self, provider: str, error_msg: str) -> None:
        if provider not in self.providers:
            return
        p = self.providers[provider]
        p["failure_count"] += 1
        p["consecutive_failures"] += 1
        p["last_error"] = str(error_msg)

        if "429" in error_msg or "rate limit" in error_msg.lower():
            p["status"] = "RATE_LIMITED"
        elif p["consecutive_failures"] >= 3:
            p["status"] = "OFFLINE"
        else:
            p["status"] = "BUSY"

    def get_average_latency(self, provider: str) -> float:
        p = self.providers.get(provider)
        if not p or not p["latencies"]:
            # Default estimated latency per provider
            defaults = {"groq": 500.0, "gemini": 800.0, "openrouter": 1200.0, "ollama": 2000.0}
            return defaults.get(provider, 1500.0)
        return sum(p["latencies"]) / len(p["latencies"])

    def get_availability_score(self, provider: str) -> float:
        p = self.providers.get(provider)
        if not p:
            return 0.0
        status = p["status"]
        if status == "ONLINE":
            return 10.0
        elif status == "BUSY":
            return 5.0
        elif status == "RATE_LIMITED":
            return 2.0
        else:  # OFFLINE
            return 0.0

    def get_latency_score(self, provider: str) -> float:
        avg_lat = self.get_average_latency(provider)
        if avg_lat < 1000:
            return 10.0
        elif avg_lat < 2000:
            return 8.0
        elif avg_lat < 4000:
            return 6.0
        else:
            return 2.0

    def get_reliability_score(self, provider: str) -> float:
        p = self.providers.get(provider)
        if not p:
            return 5.0
        total = p["success_count"] + p["failure_count"]
        if total == 0:
            return 10.0  # Fresh provider bonus
        success_ratio = p["success_count"] / total
        return round(success_ratio * 10.0, 2)


health_monitor = HealthMonitor()

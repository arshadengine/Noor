"""
brain/telemetry.py
─────────────────────────────────────────────────────
Routing Analytics & Telemetry Tracker for Noor.

Logs routing events, selected model, latency, failover counts, and success state
to data/telemetry.json for continuous learning and offline analysis.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"
TELEMETRY_FILE = DATA_DIR / "telemetry.json"


def log_telemetry_event(
    task_category: str,
    selected_model: str,
    provider: str,
    score: float,
    latency_ms: float,
    success: bool,
    failover_chain: list[str] | None = None,
    error_msg: str | None = None
) -> None:
    """Log a single LLM request telemetry record."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": time.time(),
            "task_category": task_category,
            "selected_model": selected_model,
            "provider": provider,
            "score": round(score, 2),
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "failover_chain": failover_chain or [],
            "error_msg": error_msg,
        }

        records = []
        if TELEMETRY_FILE.exists():
            try:
                records = json.loads(TELEMETRY_FILE.read_text(encoding="utf-8"))
            except Exception:
                records = []

        records.append(event)
        # Keep recent 500 events
        if len(records) > 500:
            records = records[-500:]

        TELEMETRY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Noor Telemetry] Failed to record telemetry: {e}")


def get_telemetry_stats() -> dict[str, Any]:
    """Get aggregated metrics per provider from telemetry logs."""
    if not TELEMETRY_FILE.exists():
        return {}

    try:
        records = json.loads(TELEMETRY_FILE.read_text(encoding="utf-8"))
        stats: dict[str, dict[str, float]] = {}

        for r in records:
            p = r.get("provider", "unknown")
            if p not in stats:
                stats[p] = {"total": 0, "successes": 0, "total_latency": 0.0}
            stats[p]["total"] += 1
            if r.get("success"):
                stats[p]["successes"] += 1
            stats[p]["total_latency"] += r.get("latency_ms", 0.0)

        summary = {}
        for p, s in stats.items():
            tot = s["total"]
            summary[p] = {
                "total_requests": tot,
                "success_rate": round(s["successes"] / tot, 2) if tot > 0 else 0.0,
                "avg_latency_ms": round(s["total_latency"] / tot, 2) if tot > 0 else 0.0,
            }
        return summary
    except Exception:
        return {}

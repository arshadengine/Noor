"""
brain/planner/telemetry.py
─────────────────────────────────────────────────────
TaskPlan Telemetry & Metric Logger.
Logs structured JSON events for plan generation, execution time, confidence, and status.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from brain.planner.schemas import TaskPlan

TELEMETRY_LOG_PATH = Path("D:/Noor/data/telemetry_planner.jsonl")


def log_plan_telemetry(plan: TaskPlan, execution_result: Dict[str, Any] = None) -> None:
    """Log structured JSON telemetry entry for a generated/executed TaskPlan."""
    try:
        TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "schema_version": plan.schema_version,
            "plan_id": plan.id,
            "goal": plan.goal,
            "task_type": plan.task_type.value if hasattr(plan.task_type, "value") else str(plan.task_type),
            "priority": plan.priority,
            "confidence": plan.confidence,
            "requires_confirmation": plan.requires_confirmation,
            "step_count": len(plan.steps),
            "reasoning": plan.reasoning,
            "result": execution_result or {"status": "planned_only"}
        }

        with open(TELEMETRY_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[Planner Telemetry Note] {e}")

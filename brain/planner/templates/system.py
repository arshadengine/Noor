"""
brain/planner/templates/system.py
─────────────────────────────────────────────────────
System Operations Template (Shutdown, Restart, Lock).
Enforces requires_confirmation = True for high-risk system actions.
"""

import uuid
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext


def get_system_template(command: str, context: Optional[PlanningContext] = None) -> TaskPlan:
    """Generate a TaskPlan for system power and control commands."""
    plan_id = f"plan_system_{uuid.uuid4().hex[:8]}"
    cmd_clean = command.lower().strip()

    action = "system_control"
    req_confirm = True

    if any(x in cmd_clean for x in ["shutdown", "turn off", "power off"]):
        action = "shutdown_pc"
    elif any(x in cmd_clean for x in ["restart", "reboot"]):
        action = "restart_pc"
    elif "lock" in cmd_clean:
        action = "lock_pc"
        req_confirm = False

    step = TaskStep(
        id="step_1",
        tool="system",
        action=action,
        target=cmd_clean,
        preconditions=["user_authenticated"],
        success_conditions=["system_command_dispatched"],
        timeout_sec=10.0
    )

    return TaskPlan(
        id=plan_id,
        goal=f"Execute system command '{action}'",
        task_type=TaskType.SINGLE_STEP,
        priority=5,
        estimated_duration_sec=2.0,
        requires_confirmation=req_confirm,
        confidence=0.99,
        reasoning=[
            f"Matched system operation template for '{action}'.",
            f"Set requires_confirmation={req_confirm} for safety."
        ],
        steps=[step],
        metadata={"action": action, "template": "system_control"}
    )

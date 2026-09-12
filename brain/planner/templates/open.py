"""
brain/planner/templates/open.py
─────────────────────────────────────────────────────
Open Resource Template (Apps, Folders, Files, Settings).
"""

import uuid
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext


def get_open_template(target: str, context: Optional[PlanningContext] = None) -> TaskPlan:
    """Generate a single-step or folder open TaskPlan."""
    plan_id = f"plan_open_{uuid.uuid4().hex[:8]}"
    t_clean = target.lower().strip()
    if t_clean.startswith("open "):
        t_clean = t_clean[5:].strip()

    if any(x in t_clean for x in ["folder", "directory", "dir", "downloads", "desktop", "documents"]):
        step = TaskStep(
            id="step_1",
            tool="filesystem",
            action="open_folder",
            target=target,
            preconditions=["folder_exists"],
            success_conditions=["folder_opened"],
            timeout_sec=15.0
        )
        return TaskPlan(
            id=plan_id,
            goal=f"Open folder '{target}'",
            task_type=TaskType.SINGLE_STEP,
            priority=3,
            estimated_duration_sec=3.0,
            requires_confirmation=False,
            confidence=0.98,
            reasoning=["Matched folder open trigger in template registry."],
            steps=[step],
            metadata={"target": target, "template": "open_folder"}
        )

    step = TaskStep(
        id="step_1",
        tool="launcher",
        action="open_application",
        target=target,
        preconditions=["resource_resolvable"],
        success_conditions=["process_running"],
        timeout_sec=15.0
    )
    return TaskPlan(
        id=plan_id,
        goal=f"Open resource '{target}'",
        task_type=TaskType.SINGLE_STEP,
        priority=3,
        estimated_duration_sec=3.0,
        requires_confirmation=False,
        confidence=0.95,
        reasoning=["Matched single-step application/resource open template."],
        steps=[step],
        metadata={"target": target, "template": "open_resource"}
    )

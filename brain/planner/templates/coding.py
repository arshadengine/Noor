"""
brain/planner/templates/coding.py
─────────────────────────────────────────────────────
Prepare Coding Environment Template.
Generates multi-step sequential and parallel plans for developer setup.
"""

import uuid
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext


def get_coding_template(query: str, context: Optional[PlanningContext] = None) -> TaskPlan:
    """Generate a multi-step TaskPlan for preparing a developer coding workspace."""
    plan_id = f"plan_coding_{uuid.uuid4().hex[:8]}"

    active_ws = context.active_workspace if context and context.active_workspace else "active project workspace"

    steps = [
        TaskStep(
            id="step_1",
            tool="launcher",
            action="open_application",
            target="VS Code",
            preconditions=["editor_installed"],
            success_conditions=["process_running"],
            parallel=True,
            timeout_sec=15.0
        ),
        TaskStep(
            id="step_2",
            tool="filesystem",
            action="open_folder",
            target=active_ws,
            preconditions=["workspace_exists"],
            success_conditions=["folder_opened"],
            parallel=True,
            timeout_sec=10.0
        ),
        TaskStep(
            id="step_3",
            tool="terminal",
            action="open_terminal",
            target="Windows Terminal",
            depends_on=["step_1"],
            preconditions=["terminal_available"],
            success_conditions=["terminal_running"],
            timeout_sec=10.0
        ),
        TaskStep(
            id="step_4",
            tool="browser",
            action="open_url",
            target="http://localhost:3000",
            depends_on=["step_1"],
            preconditions=["browser_available"],
            success_conditions=["url_opened"],
            timeout_sec=10.0
        ),
    ]

    return TaskPlan(
        id=plan_id,
        goal="Prepare coding workspace environment",
        task_type=TaskType.SEQUENTIAL,
        priority=4,
        estimated_duration_sec=12.0,
        requires_confirmation=False,
        confidence=0.98,
        reasoning=[
            "Detected developer coding setup request.",
            f"Using active workspace context: '{active_ws}'.",
            "Configured parallel step_1 (VS Code) and step_2 (Folder), followed by terminal and dev server browser."
        ],
        steps=steps,
        metadata={"category": "coding", "template": "prepare_coding_environment"}
    )

"""
brain/planner/templates/browser.py
─────────────────────────────────────────────────────
Web Browsing & Dev Server URL Template.
"""

import uuid
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext


def get_browser_template(url_target: str, context: Optional[PlanningContext] = None) -> TaskPlan:
    """Generate a TaskPlan for opening web URLs and dev servers."""
    plan_id = f"plan_browser_{uuid.uuid4().hex[:8]}"

    preconds = ["browser_available"]
    if "localhost" in url_target.lower() or "127.0.0.1" in url_target.lower():
        preconds.append("dev_server_running")

    step = TaskStep(
        id="step_1",
        tool="browser",
        action="open_url",
        target=url_target,
        preconditions=preconds,
        success_conditions=["url_opened"],
        timeout_sec=15.0
    )

    return TaskPlan(
        id=plan_id,
        goal=f"Open URL '{url_target}'",
        task_type=TaskType.SINGLE_STEP,
        priority=3,
        estimated_duration_sec=3.0,
        requires_confirmation=False,
        confidence=0.98,
        reasoning=[
            f"Matched browser URL template for '{url_target}'.",
            "Added preconditions for browser availability and dev server active port check."
        ],
        steps=[step],
        metadata={"url": url_target, "template": "open_url"}
    )

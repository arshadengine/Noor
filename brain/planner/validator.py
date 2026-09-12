"""
brain/planner/validator.py
─────────────────────────────────────────────────────
TaskPlan & TaskStep Validator.
Ensures plan validity, tool existence, dependency resolution, and circular dependency checks.
"""

from typing import Tuple, List
from brain.planner.schemas import TaskPlan, TaskStep


ALLOWED_TOOLS = {
    "launcher", "filesystem", "browser", "terminal", "system",
    "settings", "voice", "vision", "knowledge_graph", "none"
}


def validate_plan(plan: TaskPlan) -> Tuple[bool, List[str]]:
    """
    Validate a TaskPlan object.
    Returns (is_valid: bool, errors: list[str]).
    """
    errors = []

    if not plan:
        return False, ["TaskPlan is None or empty."]

    if not plan.id:
        errors.append("TaskPlan missing 'id'.")

    if not plan.goal:
        errors.append("TaskPlan missing 'goal'.")

    if not plan.steps and plan.task_type.value != "conversational":
        errors.append("TaskPlan has no steps for non-conversational task.")

    step_ids = {step.id for step in plan.steps}

    for i, step in enumerate(plan.steps):
        # 1. Tool check
        if step.tool not in ALLOWED_TOOLS:
            errors.append(f"Step {i+1} ('{step.id}') uses invalid tool '{step.tool}'. Allowed: {ALLOWED_TOOLS}")

        # 2. Action check
        if not step.action:
            errors.append(f"Step {i+1} ('{step.id}') missing 'action'.")

        # 3. Dependency existence check
        for dep in step.depends_on:
            if dep not in step_ids:
                errors.append(f"Step '{step.id}' depends on non-existent step '{dep}'.")
            if dep == step.id:
                errors.append(f"Step '{step.id}' cannot depend on itself.")

    # 4. Circular dependency check (Topological sort verification)
    if not errors and plan.steps:
        adj = {step.id: set(step.depends_on) for step in plan.steps}
        visited = {}  # step_id -> status: 0=unvisited, 1=visiting, 2=visited

        def has_cycle(node: str) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited.get(neighbor, 0) == 1:
                    return True
                if visited.get(neighbor, 0) == 0 and has_cycle(neighbor):
                    return True
            visited[node] = 2
            return False

        for step in plan.steps:
            if visited.get(step.id, 0) == 0:
                if has_cycle(step.id):
                    errors.append("Circular dependency detected in plan steps.")
                    break

    return len(errors) == 0, errors

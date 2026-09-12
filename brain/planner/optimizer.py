"""
brain/planner/optimizer.py
─────────────────────────────────────────────────────
TaskPlan Optimizer.
Deduplicates redundant steps, identifies parallelizable steps, and optimizes execution flow.
"""

from brain.planner.schemas import TaskPlan, TaskStep, TaskType


def optimize_plan(plan: TaskPlan) -> TaskPlan:
    """
    Optimize a TaskPlan in-place or return optimized copy.
    - Deduplicates identical steps.
    - Flags independent steps with parallel=True.
    - Recalculates estimated execution duration.
    """
    if not plan or not plan.steps:
        return plan

    seen_steps = set()
    unique_steps: list[TaskStep] = []

    for step in plan.steps:
        # Create signature for deduplication
        sig = (step.tool, step.action, step.target.lower().strip())
        if sig in seen_steps and step.tool != "none":
            # Skip duplicate step
            continue
        seen_steps.add(sig)
        unique_steps.append(step)

    plan.steps = unique_steps

    # Identify parallel steps (independent steps without dependencies)
    for step in plan.steps:
        if not step.depends_on:
            step.parallel = True

    # Recalculate duration
    parallel_duration = max((s.timeout_sec for s in plan.steps if s.parallel), default=0.0)
    sequential_duration = sum(s.timeout_sec for s in plan.steps if not s.parallel)
    plan.estimated_duration_sec = round(parallel_duration + sequential_duration, 1)

    return plan

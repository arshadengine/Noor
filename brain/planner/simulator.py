"""
brain/planner/simulator.py
─────────────────────────────────────────────────────
TaskPlan Simulator & Precondition Inspector.
Simulates a TaskPlan prior to execution to detect missing preconditions, offline services, or high risks.
"""

from typing import Dict, Any, List
from brain.planner.schemas import TaskPlan, PlanningContext
from brain.resolvers.url import URLResolver


def simulate_plan(plan: TaskPlan, context: PlanningContext) -> Dict[str, Any]:
    """
    Dry-run simulate a TaskPlan against live PlanningContext.
    Checks preconditions like dev server active listening ports or tool availability.
    """
    if not plan:
        return {
            "can_execute": False,
            "missing_preconditions": ["plan_is_null"],
            "warnings": ["Plan is missing."],
            "predicted_outcome": "Simulation Failed"
        }

    missing_preconds: List[str] = []
    warnings: List[str] = []

    # Inspect dev server socket availability if plan involves localhost
    url_resolver = URLResolver()
    active_ports = url_resolver._scan_active_dev_ports()

    for step in plan.steps:
        # Check tool availability
        if step.tool not in context.available_tools and step.tool != "none":
            missing_preconds.append(f"tool_unavailable:{step.tool}")
            warnings.append(f"Tool '{step.tool}' is not available in system environment.")

        # Check preconditions
        for pre in step.preconditions:
            if pre == "dev_server_running":
                if not active_ports:
                    warnings.append(f"Step '{step.id}': No active local development server ports detected.")
            elif pre == "user_authenticated":
                pass

    can_exec = len(missing_preconds) == 0

    outcome = "Execution Ready"
    if plan.requires_confirmation:
        outcome = "Requires User Confirmation"
    elif warnings:
        outcome = "Ready with Warnings"
    elif not can_exec:
        outcome = "Blocked by Missing Preconditions"

    return {
        "can_execute": can_exec,
        "missing_preconditions": missing_preconds,
        "warnings": warnings,
        "active_dev_ports": active_ports,
        "predicted_outcome": outcome
    }

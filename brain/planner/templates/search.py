"""
brain/planner/templates/search.py
─────────────────────────────────────────────────────
Search and Open File/Document Template.
"""

import uuid
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext


def get_search_template(query: str, context: Optional[PlanningContext] = None) -> TaskPlan:
    """Generate a 2-step TaskPlan: Search file -> Open result."""
    plan_id = f"plan_search_{uuid.uuid4().hex[:8]}"

    # Extract target search query
    search_query = query.lower().strip()
    for prefix in ["find my", "find the", "find", "search for", "open my", "open the", "open"]:
        if search_query.startswith(prefix):
            search_query = search_query[len(prefix):].strip()
            break
    for suffix in ["and open it", "and open", "file"]:
        if search_query.endswith(suffix):
            search_query = search_query[:-len(suffix)].strip()

    if not search_query:
        search_query = "document"

    steps = [
        TaskStep(
            id="step_1",
            tool="filesystem",
            action="search_file",
            target=search_query,
            parameters={"search_term": search_query},
            preconditions=["filesystem_searchable"],
            success_conditions=["file_found"],
            timeout_sec=15.0
        ),
        TaskStep(
            id="step_2",
            tool="filesystem",
            action="open_result",
            target="search_result",
            depends_on=["step_1"],
            preconditions=["step_1_succeeded"],
            success_conditions=["file_opened"],
            timeout_sec=15.0
        )
    ]

    return TaskPlan(
        id=plan_id,
        goal=f"Search for '{search_query}' and open match",
        task_type=TaskType.SEARCH_AND_ACTION,
        priority=3,
        estimated_duration_sec=6.0,
        requires_confirmation=False,
        confidence=0.96,
        reasoning=[
            f"Extracted search query term '{search_query}'.",
            "Configured 2-step plan: Step 1 (Search file) -> Step 2 (Open result)."
        ],
        steps=steps,
        metadata={"search_term": search_query, "template": "search_and_open"}
    )

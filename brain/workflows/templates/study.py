"""
brain/workflows/templates/study.py
─────────────────────────────────────────────────────
Declarative Study & Research Workflow Template for Noor.
Constructs multi-task WorkflowPlan for study and research workspace setup.
"""

from brain.planner.schemas import TaskStep
from brain.workflows.schemas import WorkflowPlan, WorkflowTask, WorkflowExecutionMode


def create_study_workflow(topic: str = "AI Research") -> WorkflowPlan:
    """Create a declarative study workflow."""
    task1 = WorkflowTask(
        task_id="task_notes",
        step=TaskStep(id="step_notes", tool="launcher", action="open_application", target="notepad"),
        weight=1.0,
        depends_on=[]
    )
    task2 = WorkflowTask(
        task_id="task_research_browser",
        step=TaskStep(id="step_research", tool="browser", action="open_url", target=f"https://www.google.com/search?q={topic}"),
        weight=2.0,
        depends_on=["task_notes"]
    )

    return WorkflowPlan(
        goal=f"Prepare study workspace for '{topic}'",
        workflow_type="STUDY",
        tasks=[task1, task2],
        execution_mode=WorkflowExecutionMode.SEQUENTIAL
    )

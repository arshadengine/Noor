"""
brain/workflows/templates/meeting.py
─────────────────────────────────────────────────────
Declarative Meeting Prep Workflow Template for Noor.
Constructs multi-task WorkflowPlan for meeting preparation.
"""

from brain.planner.schemas import TaskStep
from brain.workflows.schemas import WorkflowPlan, WorkflowTask, WorkflowExecutionMode


def create_meeting_workflow(meeting_target: str = "Google Meet") -> WorkflowPlan:
    """Create a declarative meeting workflow."""
    task1 = WorkflowTask(
        task_id="task_meeting_notes",
        step=TaskStep(id="step_notes", tool="launcher", action="open_application", target="notepad"),
        weight=1.0,
        depends_on=[]
    )
    task2 = WorkflowTask(
        task_id="task_meeting_url",
        step=TaskStep(id="step_meet", tool="browser", action="open_url", target="https://meet.google.com"),
        weight=2.0,
        depends_on=["task_meeting_notes"]
    )

    return WorkflowPlan(
        goal=f"Prepare meeting workspace for '{meeting_target}'",
        workflow_type="MEETING",
        tasks=[task1, task2],
        execution_mode=WorkflowExecutionMode.SEQUENTIAL
    )

"""
brain/workflows/templates/backup.py
─────────────────────────────────────────────────────
Declarative Backup Workflow Template for Noor.
Constructs multi-task WorkflowPlan for backup and directory verification.
"""

from brain.planner.schemas import TaskStep
from brain.workflows.schemas import WorkflowPlan, WorkflowTask, WorkflowExecutionMode


def create_backup_workflow(source_folder: str = "Downloads") -> WorkflowPlan:
    """Create a declarative backup workflow."""
    task1 = WorkflowTask(
        task_id="task_open_source",
        step=TaskStep(id="step_source", tool="filesystem", action="open_folder", target=source_folder),
        weight=1.0,
        depends_on=[]
    )

    return WorkflowPlan(
        goal=f"Backup and verify '{source_folder}'",
        workflow_type="BACKUP",
        tasks=[task1],
        execution_mode=WorkflowExecutionMode.SEQUENTIAL
    )

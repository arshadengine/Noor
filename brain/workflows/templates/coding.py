"""
brain/workflows/templates/coding.py
─────────────────────────────────────────────────────
Declarative Coding Workflow Template for Noor.
Constructs multi-task WorkflowPlan for coding environment setup (IDE, Folder, Terminal, Dev Server Browser).
"""

from brain.planner.schemas import TaskStep
from brain.workflows.schemas import WorkflowPlan, WorkflowTask, WorkflowExecutionMode


def create_coding_workflow(project_target: str = "D:/Noor") -> WorkflowPlan:
    """Create a declarative multi-task coding environment workflow."""
    task1 = WorkflowTask(
        task_id="task_ide",
        step=TaskStep(id="step_ide", tool="launcher", action="open_application", target="vs code"),
        weight=1.0,
        depends_on=[]
    )
    task2 = WorkflowTask(
        task_id="task_folder",
        step=TaskStep(id="step_folder", tool="filesystem", action="open_folder", target=project_target),
        weight=1.0,
        depends_on=["task_ide"]
    )
    task3 = WorkflowTask(
        task_id="task_terminal",
        step=TaskStep(id="step_terminal", tool="launcher", action="open_application", target="Windows Terminal"),
        weight=1.0,
        depends_on=["task_folder"]
    )
    task4 = WorkflowTask(
        task_id="task_browser",
        step=TaskStep(id="step_browser", tool="browser", action="open_url", target="http://localhost:3000"),
        weight=2.0,
        depends_on=["task_terminal"]
    )

    return WorkflowPlan(
        goal=f"Prepare coding environment for '{project_target}'",
        workflow_type="CODING",
        tasks=[task1, task2, task3, task4],
        execution_mode=WorkflowExecutionMode.HYBRID
    )

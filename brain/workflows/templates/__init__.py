"""
brain/workflows/templates/__init__.py
─────────────────────────────────────────────────────
Declarative Workflow Templates Package Exports.
"""

from brain.workflows.templates.coding import create_coding_workflow
from brain.workflows.templates.study import create_study_workflow
from brain.workflows.templates.backup import create_backup_workflow
from brain.workflows.templates.meeting import create_meeting_workflow

__all__ = [
    "create_coding_workflow",
    "create_study_workflow",
    "create_backup_workflow",
    "create_meeting_workflow",
]

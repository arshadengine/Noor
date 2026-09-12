"""
brain/runtime/inspector.py
─────────────────────────────────────────────────────
Runtime Inspector for Noor OS Task Pipeline.
Provides real-time active task summaries, progress inspection, and status queries.
"""

from typing import Dict, List, Any, Optional
from brain.runtime.task_manager import TaskManager, TaskHandle


class RuntimeInspector:
    """Provides live status inspection of Noor's runtime task system."""

    @staticmethod
    def get_active_tasks_summary() -> List[Dict[str, Any]]:
        """Return formatted summary of all active (running/queued/waiting) tasks."""
        active_handles = TaskManager.get_active_tasks()
        return [
            {
                "task_id": h.task_id,
                "goal": h.plan.goal if h.plan else "",
                "state": h.state.value,
                "progress_percent": h.progress_percent,
                "current_step_id": h.current_step_id,
                "message": h.message,
                "tags": h.tags,
                "execution_mode": h.execution_mode.value,
            }
            for h in active_handles
        ]

    @staticmethod
    def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
        """Inspect a specific task by task_id."""
        handle = TaskManager.get_task(task_id)
        if not handle:
            return None
        return handle.to_dict()

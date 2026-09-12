"""
brain/planner/task_manager.py
─────────────────────────────────────────────────────
Central Task State Manager for Noor (Phase 2.3.3).
Manages task lifecycles (QUEUED -> PREPARING -> RUNNING -> WAITING_FOR_USER -> RETRYING -> COMPLETED / FAILED / CANCELLED).
Supports task submission, progress tracking (0-100%), pause, resume, and cancellation.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from brain.planner.schemas import TaskPlan


class TaskState(Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskHandle:
    task_id: str
    plan: TaskPlan
    state: TaskState = TaskState.QUEUED
    progress_percent: float = 0.0
    start_time: str = ""
    finish_time: str = ""
    duration_sec: float = 0.0
    current_step_id: str = ""
    message: str = ""
    is_paused: bool = False
    is_cancelled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.plan.goal if self.plan else "",
            "state": self.state.value if isinstance(self.state, TaskState) else str(self.state),
            "progress_percent": self.progress_percent,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "duration_sec": self.duration_sec,
            "current_step_id": self.current_step_id,
            "message": self.message,
            "is_paused": self.is_paused,
            "is_cancelled": self.is_cancelled,
            "metadata": self.metadata,
        }


class TaskManager:
    """Central Task State Manager for Noor tasks."""

    _instance = None
    _tasks: Dict[str, TaskHandle] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._tasks = {}
        return cls._instance

    @classmethod
    def submit_task(cls, plan: TaskPlan) -> TaskHandle:
        """Queue and track a new TaskPlan."""
        from datetime import datetime
        task_id = plan.id or f"task_{uuid.uuid4().hex[:8]}"
        handle = TaskHandle(
            task_id=task_id,
            plan=plan,
            state=TaskState.QUEUED,
            start_time=datetime.now().isoformat(),
            message="Task submitted to queue."
        )
        cls._tasks[task_id] = handle
        return handle

    @classmethod
    def get_task(cls, task_id: str) -> Optional[TaskHandle]:
        return cls._tasks.get(task_id)

    @classmethod
    def get_active_tasks(cls) -> List[TaskHandle]:
        """Return all currently queued, preparing, running, or waiting tasks."""
        active_states = {TaskState.QUEUED, TaskState.PREPARING, TaskState.RUNNING, TaskState.WAITING_FOR_USER, TaskState.RETRYING}
        return [t for t in cls._tasks.values() if t.state in active_states]

    @classmethod
    def update_state(cls, task_id: str, state: TaskState, progress: float = 0.0, step_id: str = "", message: str = ""):
        """Update task lifecycle state and progress."""
        from datetime import datetime
        handle = cls.get_task(task_id)
        if handle:
            handle.state = state
            handle.progress_percent = max(0.0, min(100.0, progress))
            if step_id:
                handle.current_step_id = step_id
            if message:
                handle.message = message

            if state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                handle.finish_time = datetime.now().isoformat()
                try:
                    s_ts = datetime.fromisoformat(handle.start_time).timestamp()
                    f_ts = datetime.fromisoformat(handle.finish_time).timestamp()
                    handle.duration_sec = round(max(0.0, f_ts - s_ts), 2)
                except Exception:
                    pass

    @classmethod
    def pause_task(cls, task_id: str) -> bool:
        handle = cls.get_task(task_id)
        if handle and handle.state in (TaskState.RUNNING, TaskState.QUEUED):
            handle.is_paused = True
            handle.state = TaskState.WAITING_FOR_USER
            handle.message = "Task paused by user."
            return True
        return False

    @classmethod
    def resume_task(cls, task_id: str) -> bool:
        handle = cls.get_task(task_id)
        if handle and handle.is_paused:
            handle.is_paused = False
            handle.state = TaskState.RUNNING
            handle.message = "Task resumed."
            return True
        return False

    @classmethod
    def cancel_task(cls, task_id: str) -> bool:
        handle = cls.get_task(task_id)
        if handle and handle.state not in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            handle.is_cancelled = True
            cls.update_state(task_id, TaskState.CANCELLED, message="Task cancelled by user.")
            return True
        return False

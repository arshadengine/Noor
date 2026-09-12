"""
brain/runtime/task_manager.py
─────────────────────────────────────────────────────
Central Runtime Task State Manager for Noor (Phase 2.3.3).
Uses an In-Memory Runtime Store for fast state operations, publishes events to TaskEventBus,
manages Parent/Child DAG hierarchies, cooperative cancellation tokens, and task tags.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from brain.planner.schemas import TaskPlan
from brain.runtime.events import TaskEventBus, TaskEvent, TaskEventType
from brain.runtime.cancellation import CancellationToken
from brain.runtime.metrics import TaskMetrics


class TaskState(Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(Enum):
    IMMEDIATE = "immediate"
    BACKGROUND = "background"
    SCHEDULED = "scheduled"
    BLOCKING = "blocking"
    EXCLUSIVE = "exclusive"


class FailureReason(Enum):
    RESOURCE_NOT_FOUND = "resource_not_found"
    TIMEOUT = "timeout"
    USER_CANCELLED = "user_cancelled"
    PRECONDITION_FAILED = "precondition_failed"
    VERIFICATION_FAILED = "verification_failed"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


@dataclass
class TaskHandle:
    task_id: str
    plan: TaskPlan
    state: TaskState = TaskState.QUEUED
    execution_mode: ExecutionMode = ExecutionMode.IMMEDIATE
    progress_percent: float = 0.0
    start_time: str = ""
    finish_time: str = ""
    current_step_id: str = ""
    message: str = ""

    parent_task_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    depends_on_task_ids: List[str] = field(default_factory=list)

    tags: List[str] = field(default_factory=list)
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    metrics: TaskMetrics = field(default_factory=TaskMetrics)

    failure_reason: Optional[FailureReason] = None
    recovery_action: Optional[str] = None

    planner_version: str = "2.3.1"
    execution_version: str = "2.3.2"
    schema_version: str = "2.3.3"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.plan.goal if self.plan else "",
            "state": self.state.value if isinstance(self.state, TaskState) else str(self.state),
            "execution_mode": self.execution_mode.value if isinstance(self.execution_mode, ExecutionMode) else str(self.execution_mode),
            "progress_percent": self.progress_percent,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "current_step_id": self.current_step_id,
            "message": self.message,
            "parent_task_id": self.parent_task_id,
            "children_ids": self.children_ids,
            "depends_on_task_ids": self.depends_on_task_ids,
            "tags": self.tags,
            "metrics": self.metrics.to_dict(),
            "failure_reason": self.failure_reason.value if self.failure_reason else None,
            "recovery_action": self.recovery_action,
            "planner_version": self.planner_version,
            "execution_version": self.execution_version,
            "schema_version": self.schema_version,
        }


class TaskManager:
    """In-Memory Runtime Task State Manager."""

    _instance = None
    _tasks: Dict[str, TaskHandle] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._tasks = {}
        return cls._instance

    @classmethod
    def submit_task(cls, plan: TaskPlan, execution_mode: ExecutionMode = ExecutionMode.IMMEDIATE, tags: Optional[List[str]] = None) -> TaskHandle:
        """Queue and track a new TaskPlan in runtime store."""
        task_id = plan.id or f"task_{uuid.uuid4().hex[:8]}"

        # Infer tags if not specified
        if not tags:
            tags = []
            g_lower = plan.goal.lower()
            if "code" in g_lower or "vs" in g_lower:
                tags.append("coding")
            if "chrome" in g_lower or "url" in g_lower or "browser" in g_lower:
                tags.append("browser")
            if "download" in g_lower or "folder" in g_lower:
                tags.append("workspace")

        handle = TaskHandle(
            task_id=task_id,
            plan=plan,
            state=TaskState.QUEUED,
            execution_mode=execution_mode,
            tags=tags,
            start_time=datetime.now().isoformat(),
            message="Task submitted to runtime queue."
        )
        cls._tasks[task_id] = handle

        # Publish TASK_CREATED event
        TaskEventBus.publish(TaskEvent(
            task_id=task_id,
            event_type=TaskEventType.TASK_CREATED,
            progress_percent=0.0,
            message="Task created.",
            data=handle.to_dict()
        ))

        return handle

    @classmethod
    def get_task(cls, task_id: str) -> Optional[TaskHandle]:
        return cls._tasks.get(task_id)

    @classmethod
    def get_active_tasks(cls) -> List[TaskHandle]:
        active_states = {TaskState.QUEUED, TaskState.PREPARING, TaskState.RUNNING, TaskState.WAITING_FOR_USER, TaskState.RETRYING}
        return [t for t in cls._tasks.values() if t.state in active_states]

    @classmethod
    def update_state(cls, task_id: str, state: TaskState, progress: float = 0.0, step_id: str = "", message: str = "", failure_reason: Optional[FailureReason] = None):
        """Transition task state and publish real-time event to TaskEventBus."""
        handle = cls.get_task(task_id)
        if handle:
            handle.state = state
            handle.progress_percent = max(0.0, min(100.0, progress))
            if step_id:
                handle.current_step_id = step_id
            if message:
                handle.message = message
            if failure_reason:
                handle.failure_reason = failure_reason

            if state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                handle.finish_time = datetime.now().isoformat()

            # Map to TaskEventType
            event_map = {
                TaskState.QUEUED: TaskEventType.TASK_CREATED,
                TaskState.PREPARING: TaskEventType.TASK_STARTED,
                TaskState.RUNNING: TaskEventType.TASK_PROGRESS,
                TaskState.WAITING_FOR_USER: TaskEventType.TASK_WAITING,
                TaskState.RETRYING: TaskEventType.TASK_STARTED,
                TaskState.COMPLETED: TaskEventType.TASK_COMPLETED,
                TaskState.FAILED: TaskEventType.TASK_FAILED,
                TaskState.CANCELLED: TaskEventType.TASK_CANCELLED,
            }

            evt_type = event_map.get(state, TaskEventType.TASK_PROGRESS)
            TaskEventBus.publish(TaskEvent(
                task_id=task_id,
                event_type=evt_type,
                progress_percent=handle.progress_percent,
                message=handle.message,
                data={"step_id": step_id, "state": state.value}
            ))

    @classmethod
    def pause_task(cls, task_id: str) -> bool:
        handle = cls.get_task(task_id)
        if handle and handle.state in (TaskState.RUNNING, TaskState.QUEUED):
            cls.update_state(task_id, TaskState.WAITING_FOR_USER, progress=handle.progress_percent, message="Task paused by user.")
            return True
        return False

    @classmethod
    def resume_task(cls, task_id: str) -> bool:
        handle = cls.get_task(task_id)
        if handle and handle.state == TaskState.WAITING_FOR_USER:
            cls.update_state(task_id, TaskState.RUNNING, progress=handle.progress_percent, message="Task resumed.")
            return True
        return False

    @classmethod
    def cancel_task(cls, task_id: str, reason: str = "User requested cancellation") -> bool:
        handle = cls.get_task(task_id)
        if handle and handle.state not in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            handle.cancellation_token.cancel(reason)
            cls.update_state(task_id, TaskState.CANCELLED, message=f"Task cancelled: {reason}", failure_reason=FailureReason.USER_CANCELLED)
            return True
        return False

    @classmethod
    def clear_all(cls):
        """Clear all active and recorded tasks from memory."""
        cls._tasks.clear()

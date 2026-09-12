"""
brain/workflows/schemas.py
─────────────────────────────────────────────────────
Data Models & Schemas for Noor Workflow Orchestration (Phase 2.4).
Defines WorkflowStatus, WorkflowTask, WorkflowPlan, and WorkflowExecutionReport.
Supports weighted progress tracking (completed_weights / total_weights).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from brain.planner.schemas import TaskStep, TaskPlan


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class WorkflowTask:
    task_id: str
    step: TaskStep
    weight: float = 1.0
    depends_on: List[str] = field(default_factory=list)
    status: str = "PENDING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "step": self.step.to_dict() if hasattr(self.step, "to_dict") else str(self.step),
            "weight": self.weight,
            "depends_on": self.depends_on,
            "status": self.status,
        }


@dataclass
class WorkflowPlan:
    workflow_id: str = field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    goal: str = ""
    workflow_type: str = "GENERAL"
    version: str = "2.4.0"
    tasks: List[WorkflowTask] = field(default_factory=list)
    execution_mode: WorkflowExecutionMode = WorkflowExecutionMode.HYBRID
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_total_weight(self) -> float:
        return sum(t.weight for t in self.tasks) if self.tasks else 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "workflow_type": self.workflow_type,
            "version": self.version,
            "tasks": [t.to_dict() for t in self.tasks],
            "execution_mode": self.execution_mode.value if isinstance(self.execution_mode, WorkflowExecutionMode) else str(self.execution_mode),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class WorkflowExecutionReport:
    workflow_id: str
    goal: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    progress_percent: float = 0.0
    duration_sec: float = 0.0
    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)
    summary_messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "status": self.status.value if isinstance(self.status, WorkflowStatus) else str(self.status),
            "progress_percent": self.progress_percent,
            "duration_sec": self.duration_sec,
            "completed_task_ids": self.completed_task_ids,
            "failed_task_ids": self.failed_task_ids,
            "summary_messages": self.summary_messages,
        }

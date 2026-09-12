"""
brain/workflows/events.py
─────────────────────────────────────────────────────
Workflow Event Bus & Pub/Sub Stream for Noor Workflows.
Publishes workflow-level events to UI, voice, and telemetry subscribers.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable, Any, Optional

WORKFLOW_EVENT_VERSION = "1.0"


class WorkflowEventType(Enum):
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PROGRESS = "workflow_progress"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"


@dataclass
class WorkflowEvent:
    event_id: str = field(default_factory=lambda: f"wf_evt_{uuid.uuid4().hex[:8]}")
    event_version: str = WORKFLOW_EVENT_VERSION
    workflow_id: str = ""
    event_type: WorkflowEventType = WorkflowEventType.WORKFLOW_CREATED
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    progress_percent: float = 0.0
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_version": self.event_version,
            "workflow_id": self.workflow_id,
            "event_type": self.event_type.value if isinstance(self.event_type, WorkflowEventType) else str(self.event_type),
            "timestamp": self.timestamp,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "data": self.data,
        }


class WorkflowEventBus:
    """Pub/Sub Workflow Event Bus."""

    _listeners: List[Callable[[WorkflowEvent], None]] = []

    @classmethod
    def subscribe(cls, callback: Callable[[WorkflowEvent], None]):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[WorkflowEvent], None]):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def publish(cls, event: WorkflowEvent):
        for listener in cls._listeners:
            try:
                listener(event)
            except Exception as ex:
                print(f"[WorkflowEventBus Note] Listener exception: {ex}")

    @classmethod
    def clear(cls):
        cls._listeners.clear()

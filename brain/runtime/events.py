"""
brain/runtime/events.py
─────────────────────────────────────────────────────
Task Event Bus & Pub/Sub Event System for Noor Runtime (Phase 2.3.3).
Provides real-time event publishing, listener subscriptions, and Event Replay functionality.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable, Any, Optional

EVENT_VERSION = "1.0"


class TaskEventType(Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_WAITING = "task_waiting"
    TASK_RESUMED = "task_resumed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"


@dataclass
class TaskEvent:
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    event_version: str = EVENT_VERSION
    task_id: str = ""
    event_type: TaskEventType = TaskEventType.TASK_CREATED
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    progress_percent: float = 0.0
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_version": self.event_version,
            "task_id": self.task_id,
            "event_type": self.event_type.value if isinstance(self.event_type, TaskEventType) else str(self.event_type),
            "timestamp": self.timestamp,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "data": self.data,
        }


class TaskEventBus:
    """Pub/Sub Task Event Bus with Event Stream Replay."""

    _listeners: List[Callable[[TaskEvent], None]] = []
    _event_store: Dict[str, List[TaskEvent]] = {}  # task_id -> List[TaskEvent]

    @classmethod
    def subscribe(cls, callback: Callable[[TaskEvent], None]):
        """Subscribe a listener callback to real-time task events."""
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[TaskEvent], None]):
        """Unsubscribe a listener callback."""
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def publish(cls, event: TaskEvent):
        """Publish a task event to all active listeners and store in stream."""
        if event.task_id not in cls._event_store:
            cls._event_store[event.task_id] = []
        cls._event_store[event.task_id].append(event)

        for listener in cls._listeners:
            try:
                listener(event)
            except Exception as ex:
                print(f"[EventBus Note] Event listener exception: {ex}")

    @classmethod
    def get_event_stream(cls, task_id: str) -> List[TaskEvent]:
        """Replay stored event stream for a specific task_id."""
        return cls._event_store.get(task_id, [])

    @classmethod
    def clear(cls):
        """Reset listeners and event store."""
        cls._listeners.clear()
        cls._event_store.clear()

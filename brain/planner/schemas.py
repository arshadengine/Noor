"""
brain/planner/schemas.py
─────────────────────────────────────────────────────
Strongly-typed data models for Phase 2.3.1 Intelligent Task Planner.
Defines TaskType Enum, TaskStep, TaskPlan (schema_version="2.3.1"), and PlanningContext.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class TaskType(Enum):
    SINGLE_STEP = "single_step"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    SEARCH_AND_ACTION = "search_and_action"
    AUTOMATION = "automation"
    CONVERSATIONAL = "conversational"


@dataclass
class TaskStep:
    id: str
    tool: str  # e.g., "launcher", "filesystem", "browser", "terminal", "system", "none"
    action: str  # e.g., "open_application", "open_folder", "open_url", "search_file", "conversed_reply"
    target: str = ""  # Abstract target e.g. "project configuration", "internship report"
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    success_conditions: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    parallel: bool = False
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 2, "backoff_sec": 1.0})
    timeout_sec: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool": self.tool,
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "success_conditions": self.success_conditions,
            "depends_on": self.depends_on,
            "parallel": self.parallel,
            "retry_policy": self.retry_policy,
            "timeout_sec": self.timeout_sec,
        }


@dataclass
class TaskPlan:
    schema_version: str = "2.3.1"
    id: str = ""
    goal: str = ""
    task_type: TaskType = TaskType.SINGLE_STEP
    priority: int = 3
    estimated_duration_sec: float = 5.0
    requires_confirmation: bool = False
    confidence: float = 1.0
    reasoning: List[str] = field(default_factory=list)
    steps: List[TaskStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "goal": self.goal,
            "task_type": self.task_type.value if isinstance(self.task_type, TaskType) else str(self.task_type),
            "priority": self.priority,
            "estimated_duration_sec": self.estimated_duration_sec,
            "requires_confirmation": self.requires_confirmation,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "steps": [step.to_dict() for step in self.steps],
            "metadata": self.metadata,
        }


@dataclass
class PlanningContext:
    conversation_summary: str = ""
    active_workspace: str = ""
    active_window: str = ""
    running_apps: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    system_state: Dict[str, Any] = field(default_factory=dict)
    current_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_summary": self.conversation_summary,
            "active_workspace": self.active_workspace,
            "active_window": self.active_window,
            "running_apps": self.running_apps,
            "available_tools": self.available_tools,
            "user_preferences": self.user_preferences,
            "system_state": self.system_state,
            "current_time": self.current_time,
        }

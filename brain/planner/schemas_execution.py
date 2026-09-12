"""
brain/planner/schemas_execution.py
─────────────────────────────────────────────────────
Strongly-typed data models for Phase 2.3.2 Task Execution Engine & Verification Pipeline.
Defines ExecutionStatus, VerificationLevel, RecoveryPolicy, Evidence, StepExecutionResult,
ExecutionContext, and ExecutionReport.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ExecutionStatus(Enum):
    NOT_STARTED = "not_started"
    PREPARING = "preparing"
    RUNNING = "running"
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class VerificationLevel(Enum):
    NONE = "none"
    BASIC = "basic"        # Process PID exists
    STANDARD = "standard"   # Process + target resource handle exists
    STRONG = "strong"     # Process + window handle + foreground active focus


class RecoveryPolicy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ASK_USER = "ask_user"
    ABORT = "abort"


@dataclass
class Evidence:
    process_id: int = 0
    process_name: str = ""
    process_path: str = ""
    window_title: str = ""
    window_handle: int = 0
    in_foreground: bool = False
    launch_time: str = ""
    verification_time: str = ""
    verification_level: VerificationLevel = VerificationLevel.NONE
    raw_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "process_name": self.process_name,
            "process_path": self.process_path,
            "window_title": self.window_title,
            "window_handle": self.window_handle,
            "in_foreground": self.in_foreground,
            "launch_time": self.launch_time,
            "verification_time": self.verification_time,
            "verification_level": self.verification_level.value if isinstance(self.verification_level, VerificationLevel) else str(self.verification_level),
            "raw_details": self.raw_details,
        }


@dataclass
class StepExecutionResult:
    step_id: str
    tool: str
    action: str
    target: str
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    evidence: Evidence = field(default_factory=Evidence)
    duration_sec: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool": self.tool,
            "action": self.action,
            "target": self.target,
            "status": self.status.value if isinstance(self.status, ExecutionStatus) else str(self.status),
            "evidence": self.evidence.to_dict(),
            "duration_sec": self.duration_sec,
            "error_message": self.error_message,
        }


@dataclass
class ExecutionContext:
    plan_id: str = ""
    current_step_id: str = ""
    completed_step_ids: List[str] = field(default_factory=list)
    failed_step_ids: List[str] = field(default_factory=list)
    skipped_step_ids: List[str] = field(default_factory=list)
    retry_counts: Dict[str, int] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    is_cancelled: bool = False
    is_paused: bool = False

    def log_timeline(self, step_id: str, stage: str, status: str, message: str = ""):
        from datetime import datetime
        self.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "step_id": step_id,
            "stage": stage,
            "status": status,
            "message": message
        })


@dataclass
class ExecutionReport:
    plan_id: str = ""
    goal: str = ""
    overall_status: str = "FULLY_COMPLETE"  # FULLY_COMPLETE, PARTIALLY_COMPLETE, FAILED
    total_duration_sec: float = 0.0
    step_results: List[StepExecutionResult] = field(default_factory=list)
    verified_summary: List[str] = field(default_factory=list)
    attempted_summary: List[str] = field(default_factory=list)
    failed_summary: List[str] = field(default_factory=list)
    synthesized_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "overall_status": self.overall_status,
            "total_duration_sec": self.total_duration_sec,
            "step_results": [sr.to_dict() for sr in self.step_results],
            "verified_summary": self.verified_summary,
            "attempted_summary": self.attempted_summary,
            "failed_summary": self.failed_summary,
            "synthesized_response": self.synthesized_response,
        }

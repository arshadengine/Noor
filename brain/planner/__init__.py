"""
brain/planner/__init__.py
─────────────────────────────────────────────────────
TaskPlanner Package Exports for Noor Phase 2.3.1, 2.3.2 & 2.3.3.
Exports TaskPlanner, TaskPlan, TaskStep, TaskType, PlanningContext,
ExecutionEngine, StepVerifier, WindowManager, PostExecutionEvaluator,
ExecutionStatus, VerificationLevel, Evidence, StepExecutionResult, ExecutionReport.
"""

from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext
from brain.planner.context import gather_planning_context
from brain.planner.planner import TaskPlanner
from brain.planner.validator import validate_plan
from brain.planner.optimizer import optimize_plan
from brain.planner.simulator import simulate_plan
from brain.planner.telemetry import log_plan_telemetry

from brain.planner.schemas_execution import (
    ExecutionStatus,
    VerificationLevel,
    RecoveryPolicy,
    Evidence,
    StepExecutionResult,
    ExecutionContext,
    ExecutionReport,
)
from brain.planner.window import bring_window_to_foreground, get_window_handle_for_process
from brain.planner.verifier import StepVerifier
from brain.planner.execution import TaskExecutionEngine
from brain.planner.evaluator import PostExecutionEvaluator

__all__ = [
    "TaskPlanner",
    "TaskPlan",
    "TaskStep",
    "TaskType",
    "PlanningContext",
    "gather_planning_context",
    "validate_plan",
    "optimize_plan",
    "simulate_plan",
    "log_plan_telemetry",
    "ExecutionStatus",
    "VerificationLevel",
    "RecoveryPolicy",
    "Evidence",
    "StepExecutionResult",
    "ExecutionContext",
    "ExecutionReport",
    "bring_window_to_foreground",
    "get_window_handle_for_process",
    "StepVerifier",
    "TaskExecutionEngine",
    "PostExecutionEvaluator",
]

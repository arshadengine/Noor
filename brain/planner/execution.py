"""
brain/planner/execution.py
─────────────────────────────────────────────────────
Task Execution Engine for Noor.
Executes TaskPlan steps through a 3-stage Prepare -> Execute -> Verify lifecycle.
Activates foreground windows, gathers empirical evidence, and logs step progress timelines.
"""

import time
from datetime import datetime
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, PlanningContext
from brain.planner.schemas_execution import (
    ExecutionStatus,
    StepExecutionResult,
    ExecutionContext,
    ExecutionReport,
    RecoveryPolicy,
)
from brain.planner.verifier import StepVerifier
from brain.planner.window import bring_window_to_foreground
from brain.agents import OSAgent


class TaskExecutionEngine:
    """3-Stage Task Execution Engine."""

    def __init__(self):
        pass

    def execute_plan(self, plan: TaskPlan, context: Optional[PlanningContext] = None) -> ExecutionReport:
        """
        Execute a TaskPlan using 3-stage lifecycle:
        1. PREPARE  - Evaluate preconditions & resolve target parameters.
        2. EXECUTE  - Dispatch tool action & activate foreground window focus.
        3. VERIFY   - StepVerifier gathers empirical evidence (PID, HWND, Focus).
        """
        start_time = time.time()
        exec_ctx = ExecutionContext(plan_id=plan.id)

        from brain.runtime import TaskManager, TaskState, TaskHistoryManager

        handle = TaskManager.submit_task(plan)
        TaskManager.update_state(plan.id, TaskState.PREPARING, progress=10.0, message="Preparing plan execution...")

        report = ExecutionReport(
            plan_id=plan.id,
            goal=plan.goal,
            overall_status="FULLY_COMPLETE",
            step_results=[]
        )

        total_steps_count = max(1, len(plan.steps))

        for idx, step in enumerate(plan.steps):
            exec_ctx.current_step_id = step.id
            progress = round(((idx + 1) / float(total_steps_count)) * 100.0, 1)

            # ---------------------------------------------------------
            # STAGE 1: PREPARE
            # ---------------------------------------------------------
            TaskManager.update_state(plan.id, TaskState.PREPARING, progress=progress, step_id=step.id, message=f"Preparing step '{step.id}'")
            exec_ctx.log_timeline(step.id, "PREPARE", "START", f"Preparing target '{step.target}'")

            # Precondition Check
            failed_precond = None
            for pre in step.preconditions:
                if pre == "step_1_succeeded" and "step_1" in exec_ctx.failed_step_ids:
                    failed_precond = "step_1_failed"
                    break

            if failed_precond:
                exec_ctx.log_timeline(step.id, "PREPARE", "SKIPPED", f"Precondition failed: {failed_precond}")
                exec_ctx.skipped_step_ids.append(step.id)
                res = StepExecutionResult(
                    step_id=step.id,
                    tool=step.tool,
                    action=step.action,
                    target=step.target,
                    status=ExecutionStatus.SKIPPED,
                    error_message=f"Precondition failed: {failed_precond}"
                )
                report.step_results.append(res)
                continue

            exec_ctx.log_timeline(step.id, "PREPARE", "OK", "Target resolved.")

            # ---------------------------------------------------------
            # STAGE 2: EXECUTE
            # ---------------------------------------------------------
            TaskManager.update_state(plan.id, TaskState.RUNNING, progress=progress, step_id=step.id, message=f"Executing step '{step.id}'")
            exec_ctx.log_timeline(step.id, "EXECUTE", "START", f"Executing action '{step.action}'")
            step_start = time.time()
            raw_output = ""

            try:
                if step.tool == "none":
                    raw_output = f"Conversational goal processed for: {plan.goal}"
                else:
                    cmd_prompt = f"{step.action} {step.target}".strip()
                    if step.action in ("open_application", "open_folder", "open_url"):
                        cmd_prompt = f"open {step.target}"
                    
                    chunks = list(OSAgent.run_stream(cmd_prompt))
                    raw_output = chunks[-1] if chunks else "Action dispatched."

                if step.tool in ("launcher", "browser") or "open" in step.action:
                    bring_window_to_foreground(step.target)

                exec_ctx.log_timeline(step.id, "EXECUTE", "OK", "Action dispatched successfully.")

            except Exception as ex:
                raw_output = f"Execution Exception: {ex}"
                exec_ctx.log_timeline(step.id, "EXECUTE", "ERROR", str(ex))

            # ---------------------------------------------------------
            # STAGE 3: VERIFY
            # ---------------------------------------------------------
            exec_ctx.log_timeline(step.id, "VERIFY", "START", "Gathering empirical OS evidence...")
            status, evidence = StepVerifier.verify_step(step, raw_output)

            step_duration = round(time.time() - step_start, 2)

            res = StepExecutionResult(
                step_id=step.id,
                tool=step.tool,
                action=step.action,
                target=step.target,
                status=status,
                evidence=evidence,
                duration_sec=step_duration,
                error_message="" if status in (ExecutionStatus.VERIFIED, ExecutionStatus.PARTIALLY_VERIFIED) else raw_output
            )

            report.step_results.append(res)

            if status in (ExecutionStatus.VERIFIED, ExecutionStatus.PARTIALLY_VERIFIED):
                exec_ctx.completed_step_ids.append(step.id)
                exec_ctx.log_timeline(step.id, "VERIFY", "VERIFIED", f"Verification level: {evidence.verification_level.value}")
            else:
                exec_ctx.failed_step_ids.append(step.id)
                exec_ctx.log_timeline(step.id, "VERIFY", "FAILED", f"Step failed: {raw_output}")

        report.total_duration_sec = round(time.time() - start_time, 2)

        # Overall Status Determination
        if exec_ctx.failed_step_ids and not exec_ctx.completed_step_ids:
            report.overall_status = "FAILED"
            TaskManager.update_state(plan.id, TaskState.FAILED, progress=100.0, message="Execution failed.")
        elif exec_ctx.failed_step_ids:
            report.overall_status = "PARTIALLY_COMPLETE"
            TaskManager.update_state(plan.id, TaskState.COMPLETED, progress=100.0, message="Execution partially completed.")
        else:
            report.overall_status = "FULLY_COMPLETE"
            TaskManager.update_state(plan.id, TaskState.COMPLETED, progress=100.0, message="Execution fully completed.")

        # Persist report to SQLite
        from brain.planner.evaluator import PostExecutionEvaluator
        report = PostExecutionEvaluator.evaluate_and_synthesize(report)
        tags = handle.tags if handle else []
        TaskHistoryManager.record_task_history(plan, report, tags=tags)

        return report

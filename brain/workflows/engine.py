"""
brain/workflows/engine.py
─────────────────────────────────────────────────────
Workflow Orchestration Engine for Noor (Phase 2.4).
Coordinates multi-task DAG graphs, tracks weighted progress (completed_weights / total_weights),
publishes real-time workflow events, and delegates task steps to TaskExecutionEngine.
"""

import time
from typing import Optional
from brain.planner import TaskExecutionEngine, gather_planning_context, PlanningContext
from brain.planner.schemas import TaskPlan
from brain.workflows.schemas import WorkflowPlan, WorkflowStatus, WorkflowExecutionReport
from brain.workflows.graph import WorkflowGraphEngine
from brain.workflows.events import WorkflowEventBus, WorkflowEvent, WorkflowEventType
from brain.workflows.recovery import RecoveryStrategyRegistry


class WorkflowOrchestrator:
    """Main Workflow Orchestrator for Noor."""

    def __init__(self):
        self.exec_engine = TaskExecutionEngine()

    def execute_workflow(self, plan: WorkflowPlan, context: Optional[PlanningContext] = None) -> WorkflowExecutionReport:
        """
        Execute a multi-task WorkflowPlan DAG graph:
        1. Validate DAG graph.
        2. Topologically sort or execute ready tasks.
        3. Delegate step execution to TaskExecutionEngine.
        4. Calculate weighted progress (completed_weights / total_weights).
        5. Publish real-time events to WorkflowEventBus.
        """
        start_time = time.time()
        ctx = context or gather_planning_context(plan.goal)

        # 1. DAG Validation
        valid, err_msg = WorkflowGraphEngine.validate_dag(plan)
        if not valid:
            WorkflowEventBus.publish(WorkflowEvent(
                workflow_id=plan.workflow_id,
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                progress_percent=0.0,
                message=f"DAG Validation Failed: {err_msg}"
            ))
            return WorkflowExecutionReport(
                workflow_id=plan.workflow_id,
                goal=plan.goal,
                status=WorkflowStatus.FAILED,
                summary_messages=[f"DAG Validation Failed: {err_msg}"]
            )

        # Publish WORKFLOW_STARTED event
        WorkflowEventBus.publish(WorkflowEvent(
            workflow_id=plan.workflow_id,
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            progress_percent=0.0,
            message=f"Workflow started: '{plan.goal}'"
        ))

        completed_ids: set[str] = set()
        failed_ids: set[str] = set()
        completed_weight_sum = 0.0
        total_weight = plan.get_total_weight()
        messages = []

        # 2. Execution Loop
        while len(completed_ids) + len(failed_ids) < len(plan.tasks):
            ready_tasks = WorkflowGraphEngine.get_ready_tasks(plan, completed_ids, failed_ids)
            if not ready_tasks:
                break

            for wf_task in ready_tasks:
                wf_task.status = "RUNNING"
                
                # Wrap step into single-step TaskPlan for TaskExecutionEngine
                t_plan = TaskPlan(
                    id=wf_task.task_id,
                    goal=wf_task.step.target or wf_task.step.action,
                    steps=[wf_task.step]
                )

                # Execute task via TaskExecutionEngine
                report = self.exec_engine.execute_plan(t_plan, ctx)

                if report.overall_status in ("FULLY_COMPLETE", "PARTIALLY_COMPLETE"):
                    wf_task.status = "COMPLETED"
                    completed_ids.add(wf_task.task_id)
                    completed_weight_sum += wf_task.weight
                    messages.append(f"✅ Completed task '{wf_task.task_id}'")
                else:
                    # Attempt Self-Healing Recovery
                    condition_key = wf_task.step.target or wf_task.step.action
                    recovered = RecoveryStrategyRegistry.attempt_recovery(condition_key, {"wf_task": wf_task})
                    if recovered:
                        # Retry after recovery
                        report_retry = self.exec_engine.execute_plan(t_plan, ctx)
                        if report_retry.overall_status in ("FULLY_COMPLETE", "PARTIALLY_COMPLETE"):
                            wf_task.status = "COMPLETED"
                            completed_ids.add(wf_task.task_id)
                            completed_weight_sum += wf_task.weight
                            messages.append(f"✅ Recovered and completed task '{wf_task.task_id}'")
                            continue

                    wf_task.status = "FAILED"
                    failed_ids.add(wf_task.task_id)
                    messages.append(f"❌ Failed task '{wf_task.task_id}'")

                # Weighted Progress Calculation
                prog_pct = round((completed_weight_sum / total_weight) * 100.0, 1)

                WorkflowEventBus.publish(WorkflowEvent(
                    workflow_id=plan.workflow_id,
                    event_type=WorkflowEventType.WORKFLOW_PROGRESS,
                    progress_percent=prog_pct,
                    message=f"Task '{wf_task.task_id}' status: {wf_task.status}"
                ))

        total_dur = round(time.time() - start_time, 2)
        final_prog = round((completed_weight_sum / total_weight) * 100.0, 1)

        if failed_ids and not completed_ids:
            final_status = WorkflowStatus.FAILED
            evt_type = WorkflowEventType.WORKFLOW_FAILED
        elif failed_ids:
            final_status = WorkflowStatus.COMPLETED  # Partially completed
            evt_type = WorkflowEventType.WORKFLOW_COMPLETED
        else:
            final_status = WorkflowStatus.COMPLETED
            evt_type = WorkflowEventType.WORKFLOW_COMPLETED

        WorkflowEventBus.publish(WorkflowEvent(
            workflow_id=plan.workflow_id,
            event_type=evt_type,
            progress_percent=final_prog,
            message=f"Workflow finished with status: {final_status.value}"
        ))

        return WorkflowExecutionReport(
            workflow_id=plan.workflow_id,
            goal=plan.goal,
            status=final_status,
            progress_percent=final_prog,
            duration_sec=total_dur,
            completed_task_ids=list(completed_ids),
            failed_task_ids=list(failed_ids),
            summary_messages=messages
        )

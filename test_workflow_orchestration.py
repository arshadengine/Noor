"""
test_workflow_orchestration.py
─────────────────────────────────────────────────────
Comprehensive Acceptance & Integration Test Suite for Phase 2.4 Autonomous Workflow Orchestration.
Verifies DAG Graph Engine, WorkflowOrchestrator, Weighted Progress, WorkerPool, and RecoveryRegistry.
"""

import unittest
from brain.workflows import (
    WorkflowPlan,
    WorkflowTask,
    WorkflowStatus,
    WorkflowGraphEngine,
    WorkflowEventBus,
    WorkflowEvent,
    WorkflowEventType,
    RecoveryStrategyRegistry,
    RecoveryStrategy,
    WorkerPool,
    WorkflowOrchestrator,
)
from brain.workflows.templates import create_coding_workflow, create_study_workflow
from brain.planner.schemas import TaskStep


class TestWorkflowOrchestration(unittest.TestCase):

    def setUp(self):
        self.orchestrator = WorkflowOrchestrator()

    def test_01_dag_graph_engine_validation_and_sorting(self):
        plan = create_coding_workflow("D:/Noor")
        valid, msg = WorkflowGraphEngine.validate_dag(plan)
        self.assertTrue(valid)
        self.assertEqual(msg, "OK")

        sorted_tasks = WorkflowGraphEngine.get_topological_sort(plan)
        self.assertEqual(len(sorted_tasks), len(plan.tasks))
        self.assertEqual(sorted_tasks[0].task_id, "task_ide")

    def test_02_workflow_orchestrator_execution_and_weighted_progress(self):
        events_received = []

        def listener(evt: WorkflowEvent):
            events_received.append(evt)

        WorkflowEventBus.subscribe(listener)

        plan = create_study_workflow("Machine Learning")
        report = self.orchestrator.execute_workflow(plan)

        self.assertEqual(report.status, WorkflowStatus.COMPLETED)
        self.assertEqual(report.progress_percent, 100.0)
        self.assertGreaterEqual(len(events_received), 2)

        WorkflowEventBus.unsubscribe(listener)

    def test_03_managed_worker_pool_async_submission(self):
        executed = []

        def sample_task(val):
            executed.append(val)

        pool = WorkerPool()
        pool.submit(sample_task, "async_done")

        import time
        time.sleep(0.5)

        self.assertIn("async_done", executed)

    def test_04_recovery_strategy_registry_bounded_retry(self):
        attempts = []

        def recovery_action(ctx):
            attempts.append("recovered")
            return True

        strat = RecoveryStrategy(name="dev_server_recovery", action_handler=recovery_action, max_attempts=2)
        RecoveryStrategyRegistry.register_strategy("dev_server", strat)

        ok = RecoveryStrategyRegistry.attempt_recovery("dev_server", {})
        self.assertTrue(ok)
        self.assertEqual(len(attempts), 1)

        RecoveryStrategyRegistry.reset_attempts()


if __name__ == "__main__":
    unittest.main()

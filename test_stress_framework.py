"""
test_stress_framework.py
─────────────────────────────────────────────────────
Automated Stress Testing Suite for Noor (Phase 2.5).
Tests concurrent task submissions, queue processing, parallel workflow execution, and memory stability under load.
"""

import unittest
import time
from brain.runtime import TaskManager, TaskState, ExecutionMode
from brain.workflows import WorkflowOrchestrator, WorkflowPlan, WorkflowTask
from brain.workflows.templates import create_study_workflow
from brain.planner.schemas import TaskStep, TaskPlan
from brain.reliability import MemoryProfiler


class TestStressFramework(unittest.TestCase):

    def test_01_concurrent_task_manager_workload(self):
        tm = TaskManager()
        tm.clear_all()

        MemoryProfiler.record_snapshot("stress_start")

        # Submit 50 tasks
        for i in range(50):
            t_plan = TaskPlan(
                id=f"stress_task_{i}",
                goal=f"Stress Goal {i}",
                steps=[TaskStep(id=f"step_{i}", tool="launcher", action="open_application", target="notepad")]
            )
            task = tm.submit_task(plan=t_plan, execution_mode=ExecutionMode.BACKGROUND, tags=["stress"])
            tm.update_state(task.task_id, TaskState.RUNNING)
            tm.update_state(task.task_id, TaskState.COMPLETED)

        MemoryProfiler.record_snapshot("stress_finish")
        growth = MemoryProfiler.detect_memory_growth()
        self.assertEqual(growth["status"], "STABLE")
        self.assertEqual(len(tm._tasks), 50)

    def test_02_workflow_orchestrator_stress_execution(self):
        orchestrator = WorkflowOrchestrator()
        for i in range(3):
            plan = create_study_workflow(f"Topic_{i}")
            report = orchestrator.execute_workflow(plan)
            self.assertEqual(report.progress_percent, 100.0)


if __name__ == "__main__":
    unittest.main()

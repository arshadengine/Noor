"""
test_task_manager.py
─────────────────────────────────────────────────────
Acceptance & Integration Test Suite for Phase 2.3.3 Task State Manager & Persistent Task History.
Verifies TaskState lifecycle transitions, pause/resume/cancel API, and SQLite task_history persistence.
"""

import unittest
from brain.planner import (
    TaskPlanner,
    TaskExecutionEngine,
    TaskManager,
    TaskState,
    TaskHistoryManager,
    gather_planning_context,
)


class TestTaskManagerAndHistory(unittest.TestCase):

    def setUp(self):
        self.planner = TaskPlanner()
        self.engine = TaskExecutionEngine()
        self.context = gather_planning_context("test task manager")

    def test_01_task_state_lifecycle_transitions(self):
        plan = self.planner.create_plan("Open Downloads", self.context)
        handle = TaskManager.submit_task(plan)

        self.assertIsNotNone(handle)
        self.assertEqual(handle.task_id, plan.id)
        self.assertEqual(handle.state, TaskState.QUEUED)

        # Execute plan (which transitions states to PREPARING -> RUNNING -> COMPLETED)
        report = self.engine.execute_plan(plan, self.context)
        
        updated_handle = TaskManager.get_task(plan.id)
        self.assertEqual(updated_handle.state, TaskState.COMPLETED)
        self.assertEqual(updated_handle.progress_percent, 100.0)

    def test_02_task_pause_resume_and_cancellation(self):
        plan = self.planner.create_plan("Open Chrome", self.context)
        handle = TaskManager.submit_task(plan)

        # Pause
        ok_pause = TaskManager.pause_task(handle.task_id)
        self.assertTrue(ok_pause)
        self.assertEqual(handle.state, TaskState.WAITING_FOR_USER)
        self.assertTrue(handle.is_paused)

        # Resume
        ok_resume = TaskManager.resume_task(handle.task_id)
        self.assertTrue(ok_resume)
        self.assertEqual(handle.state, TaskState.RUNNING)

        # Cancel
        ok_cancel = TaskManager.cancel_task(handle.task_id)
        self.assertTrue(ok_cancel)
        self.assertEqual(handle.state, TaskState.CANCELLED)

    def test_03_sqlite_task_history_persistence_and_query(self):
        plan = self.planner.create_plan("Prepare my coding environment", self.context)
        report = self.engine.execute_plan(plan, self.context)

        history_records = TaskHistoryManager.query_task_history(limit=5)
        self.assertGreaterEqual(len(history_records), 1)

        latest = history_records[0]
        self.assertIn("goal", latest)
        self.assertIn("duration_sec", latest)
        self.assertIn("success_rate", latest)
        self.assertIn("verified_count", latest)


if __name__ == "__main__":
    unittest.main()

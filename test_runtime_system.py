"""
test_runtime_system.py
─────────────────────────────────────────────────────
Comprehensive Acceptance & Integration Test Suite for Phase 2.3.3 Dedicated Task Runtime System (brain/runtime).
Verifies TaskEventBus Pub/Sub & Replay, CancellationToken, TaskManager lifecycle, RuntimeInspector, and SQLite History Analytics.
"""

import unittest
from brain.planner import TaskPlanner, TaskExecutionEngine, gather_planning_context
from brain.runtime import (
    TaskEventBus,
    TaskEvent,
    TaskEventType,
    CancellationToken,
    TaskManager,
    TaskState,
    RuntimeInspector,
    TaskHistoryManager,
)


class TestRuntimeSystem(unittest.TestCase):

    def setUp(self):
        self.planner = TaskPlanner()
        self.engine = TaskExecutionEngine()
        self.context = gather_planning_context("test runtime system")

    def test_01_event_bus_pub_sub_and_stream_replay(self):
        events_received = []

        def listener(evt: TaskEvent):
            events_received.append(evt)

        TaskEventBus.subscribe(listener)

        plan = self.planner.create_plan("Open Chrome", self.context)
        report = self.engine.execute_plan(plan, self.context)

        # Verify listener received real-time events
        self.assertGreaterEqual(len(events_received), 1)

        # Verify stream replay for task_id
        stream = TaskEventBus.get_event_stream(plan.id)
        self.assertGreaterEqual(len(stream), 1)
        self.assertEqual(stream[0].task_id, plan.id)

        TaskEventBus.unsubscribe(listener)

    def test_02_cooperative_cancellation_token(self):
        token = CancellationToken()
        self.assertFalse(token.is_cancelled())

        token.cancel("User aborted task")
        self.assertTrue(token.is_cancelled())
        self.assertEqual(token.reason, "User aborted task")

    def test_03_runtime_inspector(self):
        plan = self.planner.create_plan("Open Downloads", self.context)
        handle = TaskManager.submit_task(plan)

        summary = RuntimeInspector.get_active_tasks_summary()
        self.assertGreaterEqual(len(summary), 1)

        status_info = RuntimeInspector.get_task_status(handle.task_id)
        self.assertIsNotNone(status_info)
        self.assertEqual(status_info["task_id"], handle.task_id)

    def test_04_sqlite_history_tag_search_and_analytics(self):
        plan = self.planner.create_plan("Prepare my coding environment", self.context)
        report = self.engine.execute_plan(plan, self.context)

        # Search history by tag 'coding'
        coding_tasks = TaskHistoryManager.query_by_tag("coding")
        self.assertGreaterEqual(len(coding_tasks), 1)

        # Get stats today
        stats = TaskHistoryManager.get_stats_today()
        self.assertIn("total_tasks_today", stats)
        self.assertGreaterEqual(stats["total_tasks_today"], 1)


if __name__ == "__main__":
    unittest.main()

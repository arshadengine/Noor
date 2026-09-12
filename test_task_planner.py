"""
test_task_planner.py
─────────────────────────────────────────────────────
Comprehensive Acceptance & Integration Test Suite for Phase 2.3.1 Intelligent Task Planner.
Verifies plan creation, schema compliance, abstract targets, preconditions, validation, simulation, and telemetry.
"""

import unittest
import os
from brain.planner import (
    TaskPlanner,
    TaskPlan,
    TaskStep,
    TaskType,
    PlanningContext,
    gather_planning_context,
    validate_plan,
    optimize_plan,
    simulate_plan,
)


class TestTaskPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = TaskPlanner()
        self.context = gather_planning_context("test query")

    def test_01_single_step_chrome(self):
        plan = self.planner.create_plan("Open Chrome", self.context)
        self.assertEqual(plan.schema_version, "2.3.1")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool, "launcher")
        self.assertEqual(plan.steps[0].action, "open_application")
        self.assertFalse(plan.requires_confirmation)
        self.assertGreaterEqual(plan.confidence, 0.90)

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_02_folder_downloads(self):
        plan = self.planner.create_plan("Open Downloads", self.context)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool, "filesystem")
        self.assertEqual(plan.steps[0].action, "open_folder")

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_03_browser_localhost(self):
        plan = self.planner.create_plan("Open localhost", self.context)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool, "browser")
        self.assertEqual(plan.steps[0].action, "open_url")
        self.assertIn("dev_server_running", plan.steps[0].preconditions)

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_04_search_and_open_report(self):
        plan = self.planner.create_plan("Find my report and open it", self.context)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.task_type, TaskType.SEARCH_AND_ACTION)
        self.assertEqual(plan.steps[0].action, "search_file")
        self.assertEqual(plan.steps[1].action, "open_result")
        self.assertIn("step_1", plan.steps[1].depends_on)

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_05_prepare_coding_environment(self):
        plan = self.planner.create_plan("Prepare my coding environment", self.context)
        self.assertGreaterEqual(len(plan.steps), 3)
        self.assertEqual(plan.task_type, TaskType.SEQUENTIAL)
        tools = [s.tool for s in plan.steps]
        self.assertIn("launcher", tools)
        self.assertIn("filesystem", tools)
        self.assertIn("terminal", tools)

        # Verify parallel steps
        self.assertTrue(plan.steps[0].parallel)
        self.assertTrue(plan.steps[1].parallel)

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_06_shutdown_system_confirmation(self):
        plan = self.planner.create_plan("Shutdown PC", self.context)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool, "system")
        self.assertTrue(plan.requires_confirmation)

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_07_conversational_joke(self):
        plan = self.planner.create_plan("Tell me a joke", self.context)
        self.assertEqual(plan.task_type, TaskType.CONVERSATIONAL)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool, "none")
        self.assertEqual(plan.steps[0].action, "conversed_reply")
        self.assertFalse(plan.requires_confirmation)

        # Validate plan
        is_valid, errors = validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_08_validator_circular_dependency_check(self):
        bad_plan = TaskPlan(
            id="bad_plan",
            goal="Circular test",
            task_type=TaskType.SEQUENTIAL,
            steps=[
                TaskStep(id="step_1", tool="launcher", action="open_app", depends_on=["step_2"]),
                TaskStep(id="step_2", tool="launcher", action="open_app", depends_on=["step_1"])
            ]
        )
        is_valid, errors = validate_plan(bad_plan)
        self.assertFalse(is_valid)
        self.assertTrue(any("Circular dependency" in e for e in errors))

    def test_09_simulator_preconditions(self):
        plan = self.planner.create_plan("Open localhost", self.context)
        sim_res = simulate_plan(plan, self.context)
        self.assertIn("can_execute", sim_res)
        self.assertIn("predicted_outcome", sim_res)
        self.assertTrue(sim_res["can_execute"])

    def test_10_plan_telemetry_logging(self):
        plan = self.planner.create_plan("Open Chrome", self.context)
        telemetry_file = "D:/Noor/data/telemetry_planner.jsonl"
        self.assertTrue(os.path.exists(telemetry_file))


if __name__ == "__main__":
    unittest.main()

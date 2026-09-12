"""
test_execution_engine.py
─────────────────────────────────────────────────────
Comprehensive Acceptance & Integration Test Suite for Phase 2.3.2 Execution Engine & Verification Pipeline.
Verifies 3-stage lifecycle, foreground window focus, empirical evidence, verification levels, and honest synthesizer.
"""

import unittest
from brain.planner import (
    TaskPlanner,
    TaskExecutionEngine,
    PostExecutionEvaluator,
    StepVerifier,
    bring_window_to_foreground,
    ExecutionStatus,
    VerificationLevel,
    gather_planning_context,
)


class TestExecutionEngine(unittest.TestCase):

    def setUp(self):
        self.planner = TaskPlanner()
        self.engine = TaskExecutionEngine()
        self.evaluator = PostExecutionEvaluator()
        self.context = gather_planning_context("test engine")

    def test_01_single_step_execution_and_verification(self):
        plan = self.planner.create_plan("Open Chrome", self.context)
        report = self.engine.execute_plan(plan, self.context)
        report = self.evaluator.evaluate_and_synthesize(report)

        self.assertIn(report.overall_status, ("FULLY_COMPLETE", "PARTIALLY_COMPLETE"))
        self.assertGreaterEqual(len(report.step_results), 1)

        step_res = report.step_results[0]
        self.assertIn(step_res.status, (ExecutionStatus.VERIFIED, ExecutionStatus.PARTIALLY_VERIFIED))
        self.assertIsNotNone(step_res.evidence)

    def test_02_foreground_window_focus_call(self):
        # Test foreground window focus helper
        ok = bring_window_to_foreground("explorer.exe")
        # Should return boolean without crashing
        self.assertIsInstance(ok, bool)

    def test_03_structured_evidence_collection(self):
        plan = self.planner.create_plan("Open Downloads", self.context)
        report = self.engine.execute_plan(plan, self.context)
        report = self.evaluator.evaluate_and_synthesize(report)

        step_res = report.step_results[0]
        evidence = step_res.evidence
        self.assertIsNotNone(evidence.verification_time)
        self.assertIsInstance(evidence.verification_level, VerificationLevel)

    def test_04_honest_status_synthesizer_no_fake_claims(self):
        plan = self.planner.create_plan("Prepare my coding environment", self.context)
        report = self.engine.execute_plan(plan, self.context)
        report = self.evaluator.evaluate_and_synthesize(report)

        # Synthesized response must NOT claim fake extension installs or python selections
        resp = report.synthesized_response
        self.assertNotIn("Installed the required extensions", resp)
        self.assertNotIn("Selected the Python interpreter", resp)
        self.assertIn("Verified Actions", resp)

    def test_05_conversational_step_verification(self):
        plan = self.planner.create_plan("Tell me a joke", self.context)
        report = self.engine.execute_plan(plan, self.context)
        report = self.evaluator.evaluate_and_synthesize(report)

        self.assertEqual(report.overall_status, "FULLY_COMPLETE")
        self.assertEqual(report.step_results[0].status, ExecutionStatus.VERIFIED)


if __name__ == "__main__":
    unittest.main()

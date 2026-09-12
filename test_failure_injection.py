"""
test_failure_injection.py
─────────────────────────────────────────────────────
Failure Injection & Self-Healing Verification Suite for Noor (Phase 2.5).
Simulates API 429 rate limit outages, missing executables, locked files, and process failures.
"""

import unittest
from brain.workflows.recovery import RecoveryStrategyRegistry, RecoveryStrategy
from brain.reliability import SystemHealthMonitor, HealthStatus


class TestFailureInjection(unittest.TestCase):

    def test_01_api_429_provider_failure_injection_and_degradation(self):
        SystemHealthMonitor.register_subsystem("OpenRouter")
        SystemHealthMonitor.record_error("OpenRouter", "HTTP 429 Rate Limit Exceeded")
        SystemHealthMonitor.record_error("OpenRouter", "HTTP 429 Rate Limit Exceeded")

        reports = SystemHealthMonitor.get_all_reports()
        self.assertEqual(reports["openrouter"]["status"], "degraded")

    def test_02_missing_executable_recovery_injection(self):
        attempts = []

        def recover_missing_app(ctx):
            attempts.append("downloaded_or_located")
            return True

        strat = RecoveryStrategy(name="missing_app_recovery", action_handler=recover_missing_app, max_attempts=2)
        RecoveryStrategyRegistry.register_strategy("missing_app", strat)

        ok = RecoveryStrategyRegistry.attempt_recovery("missing_app", {})
        self.assertTrue(ok)
        self.assertEqual(len(attempts), 1)

        RecoveryStrategyRegistry.reset_attempts()


if __name__ == "__main__":
    unittest.main()

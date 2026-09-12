"""
test_reliability_framework.py
─────────────────────────────────────────────────────
Test Suite for Noor Phase 2.5 Reliability Core & Observability.
Verifies HealthMonitor, TaskTraceContext, Watchdog, MetricsCollector, MemoryProfiler, and SystemDiagnostics snapshot.
"""

import unittest
from brain.reliability import (
    SystemHealthMonitor,
    HealthStatus,
    TaskTraceContext,
    RuntimeWatchdog,
    SystemMetricsCollector,
    MemoryProfiler,
    SystemDiagnostics,
    HeartbeatDaemon,
)


class TestReliabilityFramework(unittest.TestCase):

    def test_01_health_monitor_score_and_registration(self):
        SystemHealthMonitor.register_subsystem("Model Router")
        SystemHealthMonitor.record_success("Model Router", latency_ms=45.0)

        reports = SystemHealthMonitor.get_all_reports()
        self.assertIn("model router", reports)
        self.assertEqual(reports["model router"]["status"], "online")
        self.assertGreaterEqual(reports["model router"]["health_score"], 90.0)

        score = SystemHealthMonitor.get_overall_health_score()
        self.assertGreaterEqual(score, 90.0)

    def test_02_task_trace_context_propagation(self):
        trace = TaskTraceContext(task_id="task_123", workflow_id="wf_456")
        span = trace.start_span("execution")
        span.finish(status="OK")

        data = trace.to_dict()
        self.assertEqual(data["task_id"], "task_123")
        self.assertEqual(data["workflow_id"], "wf_456")
        self.assertEqual(len(data["spans"]), 1)
        self.assertEqual(data["spans"][0]["name"], "execution")

    def test_03_watchdog_thread_inspection(self):
        watchdog_data = RuntimeWatchdog.check_health_and_stalls()
        self.assertEqual(watchdog_data["status"], "HEALTHY")
        self.assertGreater(watchdog_data["total_threads"], 0)

    def test_04_metrics_and_memory_profiling(self):
        metrics = SystemMetricsCollector.get_process_metrics()
        self.assertGreater(metrics["rss_mb"], 0.0)

        MemoryProfiler.record_snapshot("initial")
        MemoryProfiler.record_snapshot("checkpoint")
        growth = MemoryProfiler.detect_memory_growth()
        self.assertEqual(growth["status"], "STABLE")

    def test_05_system_diagnostics_unified_snapshot(self):
        snapshot = SystemDiagnostics.get_system_diagnostics_snapshot()
        self.assertIn("overall_reliability_score", snapshot)
        self.assertIn("system_health", snapshot)
        self.assertIn("process_metrics", snapshot)
        self.assertIn("hardware_metrics", snapshot)
        self.assertGreaterEqual(snapshot["overall_reliability_score"], 0.0)


if __name__ == "__main__":
    unittest.main()

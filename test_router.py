"""
test_router.py
─────────────────────────────────────────────────────
Comprehensive Test Suite for Noor Phase 2.1 Intelligent Model Router.
"""

import sys
import unittest
from pathlib import Path

# Ensure D:\Noor is in python path
sys.path.insert(0, str(Path(__file__).parent))

from brain.intent import classify_intent
from brain.registry import MODELS, check_constraints
from brain.health import health_monitor
from brain.scoring import calculate_model_score, rank_candidate_models
from brain.cache import routing_cache
from brain.telemetry import log_telemetry_event, get_telemetry_stats
from brain.llm import simple_query, chat


class TestNoorModelRouter(unittest.TestCase):

    def setUp(self):
        routing_cache.clear()

    def test_01_intent_classification(self):
        """Test Stage 1 Intent Classifier for different task categories."""
        cat, constraints = classify_intent("Write a Python script for a FastAPI web server")
        self.assertEqual(cat, "CODING")

        cat, constraints = classify_intent("Fix this traceback error in my code")
        self.assertEqual(cat, "DEBUGGING")

        cat, constraints = classify_intent("🖼️ [Attached Image]: C:/images/sample.png Describe image")
        self.assertEqual(cat, "VISION")
        self.assertTrue(constraints.get("vision"))

        cat, constraints = classify_intent("Open VS Code")
        self.assertEqual(cat, "OS_CONTROL")

        cat, constraints = classify_intent("What did I tell you yesterday?")
        self.assertEqual(cat, "MEMORY")

    def test_02_model_constraints(self):
        """Test constraint filter rejecting models lacking required features."""
        # Groq Llama 70b lacks vision constraint
        valid_groq, reason = check_constraints("groq_llama70b", {"vision": True})
        self.assertFalse(valid_groq)

        # Gemini Flash supports vision constraint
        valid_gemini, reason = check_constraints("gemini_flash", {"vision": True})
        self.assertTrue(valid_gemini)

    def test_03_scoring_and_ranking(self):
        """Test candidate model ranking and tie-breaker score computation."""
        # Coding task should rank Groq or Gemini high
        ranked = rank_candidate_models(task_category="CODING", required_constraints={})
        self.assertTrue(len(ranked) > 0)
        top_model, top_score = ranked[0]
        self.assertIn(top_model, ["groq_llama70b", "gemini_flash"])
        self.assertGreater(top_score, 6.0)

    def test_04_decision_cache(self):
        """Test short-term routing decision cache."""
        routing_cache.set("CODING", "groq_llama70b", "speed")
        cached = routing_cache.get("CODING", "speed")
        self.assertEqual(cached, "groq_llama70b")

    def test_05_telemetry_logging(self):
        """Test telemetry logging and stats aggregation."""
        log_telemetry_event(
            task_category="CODING",
            selected_model="groq_llama70b",
            provider="groq",
            score=9.5,
            latency_ms=450.0,
            success=True
        )
        stats = get_telemetry_stats()
        self.assertIn("groq", stats)
        self.assertGreaterEqual(stats["groq"]["total_requests"], 1)

    def test_06_end_to_end_router_query(self):
        """Test simple_query execution routed through Stage 2 LLM Router."""
        resp = simple_query("Reply with the single word: OK")
        self.assertTrue(len(resp) > 0)
        self.assertNotIn("⚠️ [Noor Error] All available cloud and local LLM providers failed", resp)


if __name__ == "__main__":
    unittest.main()

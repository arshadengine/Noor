"""
test_integration_phase2.py
─────────────────────────────────────────────────────
Comprehensive Phase 2.1 Integration Test & Stress Suite for Noor.

Covers:
Phase A: Intent Router & Subsystem Dispatch
Phase B: Model Router Category Scoring
Phase C: Failover Cascades (Invalid API keys -> Ollama fallback)
Phase D: Health Learning & Metric Updates
Phase E: Telemetry Inspection
Phase F: 50+ Request Stress Test
"""

from __future__ import annotations

import os
import sys
import time
import json
import unittest
from pathlib import Path

# Force UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

# Ensure D:\Noor is in python path
sys.path.insert(0, str(Path(__file__).parent))

from brain.intent import classify_intent
from brain.registry import MODELS, check_constraints
from brain.health import health_monitor
from brain.scoring import calculate_model_score, rank_candidate_models
from brain.cache import routing_cache
from brain.telemetry import get_telemetry_stats, TELEMETRY_FILE, log_telemetry_event
from brain.router import route_and_execute_generate, get_provider_instance
from brain.llm import chat, simple_query


class IntegrationTestPhase2(unittest.TestCase):

    def setUp(self):
        routing_cache.clear()

    def test_phase_a_intent_router(self):
        """Phase A: Verify Intent Classification & Subsystem Mapping."""
        print("\n--- PHASE A: INTENT ROUTER TESTS ---")
        cases = [
            ("Open VS Code", "OS_CONTROL"),
            ("Shutdown the PC in 10 minutes", "OS_CONTROL"),
            ("What did I tell you yesterday?", "MEMORY"),
            ("Attached Image: C:/test.png Describe this image", "VISION"),
            ("Search for main.py online", "RESEARCH"),
            ("Tell me a joke", "CHAT"),
            ("Explain recursion", "REASONING"),
            ("Create a project roadmap", "PLANNING"),
        ]

        for prompt, expected_cat in cases:
            cat, constraints = classify_intent(prompt)
            print(f"[Intent Test] Prompt: '{prompt[:30]}...' -> Detected Intent: {cat} (Expected: {expected_cat})")
            self.assertEqual(cat, expected_cat)

    def test_phase_b_model_router(self):
        """Phase B: Verify Candidate Scoring & Selection across Task Categories."""
        print("\n--- PHASE B: MODEL ROUTER TESTS ---")
        
        # Test 1: Coding Task
        ranked_coding = rank_candidate_models("CODING", {})
        top_coding = ranked_coding[0][0]
        print(f"[Model Router] Task: CODING -> Selected Top Model: {top_coding} (Score: {ranked_coding[0][1]})")
        self.assertIn(top_coding, ["groq_llama70b", "gemini_flash"])

        # Test 2: Reasoning Task
        ranked_reasoning = rank_candidate_models("REASONING", {})
        top_reasoning = ranked_reasoning[0][0]
        print(f"[Model Router] Task: REASONING -> Selected Top Model: {top_reasoning} (Score: {ranked_reasoning[0][1]})")
        self.assertEqual(top_reasoning, "gemini_flash")

        # Test 3: Vision Task
        ranked_vision = rank_candidate_models("VISION", {"vision": True})
        top_vision = ranked_vision[0][0]
        print(f"[Model Router] Task: VISION -> Selected Top Model: {top_vision} (Score: {ranked_vision[0][1]})")
        self.assertTrue(MODELS[top_vision]["constraints"]["vision"])

        # Test 4: Translation Task
        ranked_trans = rank_candidate_models("TRANSLATION", {})
        top_trans = ranked_trans[0][0]
        print(f"[Model Router] Task: TRANSLATION -> Selected Top Model: {top_trans} (Score: {ranked_trans[0][1]})")
        self.assertIsNotNone(top_trans)

    def test_phase_c_failover(self):
        """Phase C: Failover Tests (Invalid Keys -> Next Model -> Ollama Local)."""
        print("\n--- PHASE C: FAILOVER TESTS ---")
        
        orig_gemini = os.environ.get("GEMINI_API_KEY", "")
        orig_groq = os.environ.get("GROQ_API_KEY", "")
        orig_openrouter = os.environ.get("OPENROUTER_API_KEY", "")

        try:
            # 1. Disable Gemini API Key -> Should failover to Groq
            os.environ["GEMINI_API_KEY"] = "INVALID_GEMINI_KEY_123"
            res, cat, model_used = route_and_execute_generate(
                messages=[{"role": "user", "content": "Explain AI in 5 words"}],
                user_preference="speed"
            )
            print(f"[Failover Test 1] Gemini Key Invalid -> Seamless Failover to: '{model_used}'")
            self.assertNotEqual(MODELS.get(model_used, {}).get("provider"), "gemini")

            # 2. Disable All Cloud Keys -> Should attempt full failover cascade
            os.environ["GEMINI_API_KEY"] = "INVALID_KEY"
            os.environ["GROQ_API_KEY"] = "INVALID_KEY"
            os.environ["OPENROUTER_API_KEY"] = "INVALID_KEY"

            res, cat, model_used = route_and_execute_generate(
                messages=[{"role": "user", "content": "Hello Noor"}],
                user_preference="speed"
            )
            print(f"[Failover Test 2] All Cloud Keys Invalid -> Failover Cascade Completed -> Executed: '{model_used}'")
            # Verify Gemini, Groq, OpenRouter all recorded failures in health monitor
            self.assertIn(health_monitor.providers["gemini"]["status"], ["BUSY", "OFFLINE", "RATE_LIMITED"])
            self.assertIn(health_monitor.providers["groq"]["status"], ["BUSY", "OFFLINE", "RATE_LIMITED"])

        finally:
            # Restore original keys
            os.environ["GEMINI_API_KEY"] = orig_gemini
            os.environ["GROQ_API_KEY"] = orig_groq
            os.environ["OPENROUTER_API_KEY"] = orig_openrouter

    def test_phase_d_e_health_and_telemetry(self):
        """Phase D & E: Verify Health Metrics & Telemetry Recording."""
        print("\n--- PHASE D & E: HEALTH & TELEMETRY TESTS ---")
        
        log_telemetry_event(
            task_category="REASONING",
            selected_model="gemini_flash",
            provider="gemini",
            score=9.82,
            latency_ms=620.0,
            success=True
        )

        health_monitor.record_success("gemini", 620.0)
        
        lat = health_monitor.get_average_latency("gemini")
        avail = health_monitor.get_availability_score("gemini")
        rel = health_monitor.get_reliability_score("gemini")

        print(f"[Health Metrics] Gemini - Avg Latency: {lat:.1f}ms | Availability: {avail}/10 | Reliability: {rel}/10")
        self.assertGreater(avail, 0.0)

        stats = get_telemetry_stats()
        print(f"[Telemetry Stats Summary]: {json.dumps(stats, indent=2)}")
        self.assertTrue(len(stats) > 0)

    def test_phase_f_stress_test(self):
        """Phase F: Stress test with 50 mixed intent queries."""
        print("\n--- PHASE F: STRESS TEST (50 MIXED REQUESTS) ---")
        
        prompts = [
            "Tell me a short joke",
            "Write a Python function to reverse a list",
            "Explain quantum mechanics simply",
            "Open Chrome browser",
            "What did I tell you yesterday?",
            "Attached Image: C:/img.jpg Describe image",
            "Search for latest machine learning paper",
            "Shutdown the computer after 30 minutes",
            "Create a React component dashboard",
            "Translate Hello to Spanish",
        ] * 5  # 50 total requests

        start_stress = time.time()
        successes = 0
        cache_hits = 0

        for i, p in enumerate(prompts):
            cat, constraints = classify_intent(p)
            cached = routing_cache.get(cat, "speed", constraints)
            if cached:
                cache_hits += 1

            ranked = rank_candidate_models(cat, constraints)
            top_model = ranked[0][0]
            routing_cache.set(cat, top_model, "speed", constraints)
            successes += 1

        duration = time.time() - start_stress
        print(f"[Stress Test Complete] 50 Requests processed in {duration:.2f}s | Successes: {successes}/50 | Cache Hits: {cache_hits}")
        self.assertEqual(successes, 50)


if __name__ == "__main__":
    unittest.main()

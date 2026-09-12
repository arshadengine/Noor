"""
test_hallucinations_and_projects.py
─────────────────────────────────────────────────────
Verification test suite for Noor Phase 2.1:
Anti-Hallucination Architecture & Project Context Engine.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Force UTF-8 output on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from brain.project_engine import detect_active_project, load_project_context, load_registry
from brain.llm import verify_and_check_hallucination, chat

class TestAntiHallucinationAndProjects(unittest.TestCase):

    def test_1_project_detection(self):
        print("\n--- Running Test 1: Project Detection ---")
        # Simulate active window for TASKAS in VS Code
        proj = detect_active_project("App.js - TASKAS - Visual Studio Code", "Code.exe")
        self.assertIsNotNone(proj)
        self.assertEqual(proj["name"], "TASKAS")
        self.assertEqual(proj["path"].replace("\\", "/"), "D:/TASKAS")
        print(f"Success: Detected active project: {proj['name']} at {proj['path']}")

    def test_2_project_context_loading(self):
        print("\n--- Running Test 2: Project Context Loading ---")
        # Load context for Noor project (which definitely exists)
        context = load_project_context("Noor")
        self.assertIsNotNone(context)
        self.assertIn("Project Context: Noor", context)
        self.assertIn("D:/Noor", context.replace("\\", "/"))
        print("Success: Loaded context for Noor project:")
        # Safe encoding print
        print(context[:300].encode('utf-8', errors='ignore').decode('utf-8') + "\n...")

    def test_3_verify_impossible_question(self):
        print("\n--- Running Test 3: Impossible Question (No Evidence) ---")
        # Force an impossible question with no context
        msg = "What project did I edit on January 3rd 2024?"
        draft_resp = "You edited the TASKAS project on that day."
        context = [] # Empty context
        
        verified_resp, confidence = verify_and_check_hallucination(msg, draft_resp, context)
        print(f"Query: {msg}")
        print(f"Raw Response: {draft_resp}")
        print(f"Verified Response: {verified_resp}")
        print(f"Confidence: {confidence}")
        
        self.assertAlmostEqual(confidence, 0.0)
        self.assertIn("couldn't find any local records", verified_resp.lower())

    def test_4_hallucination_prevention(self):
        print("\n--- Running Test 4: Fabricated File Hallucination Prevention ---")
        # Ask what file was edited, context contains README.md, but response fabricates taskas_homepage.jsx
        msg = "What file did I edit yesterday?"
        draft_resp = "You modified taskas_homepage.jsx yesterday."
        context = ["Activity Log: Arshad modified README.md yesterday at 14:00."]
        
        verified_resp, confidence = verify_and_check_hallucination(msg, draft_resp, context)
        print(f"Query: {msg}")
        print(f"Context: {context}")
        print(f"Raw Response: {draft_resp}")
        print(f"Verified Response: {verified_resp}")
        print(f"Confidence: {confidence}")
        
        self.assertAlmostEqual(confidence, 0.3)
        self.assertIn("couldn't find verified records of the file 'taskas_homepage.jsx'", verified_resp.lower())

    def test_5_retrieve_before_generate_flow(self):
        print("\n--- Running Test 5: Retrieval Before Generation ---")
        # Call chat on a historical query with no local records or context
        session_id = "test-session-verify"
        query = "What project did I edit on January 3rd 2024?"
        
        # We mock the database/semantic context to be empty
        with patch("brain.llm.retrieve_context", return_value=[]), \
             patch("brain.memory.get_preference", return_value=""):
            
            # Since stream is True, it will yield tokens. We collect them.
            tokens = []
            for token, mode in chat(query, session_id, stream=True):
                tokens.append(token)
            full_resp = "".join(tokens)
            print(f"Query: {query}")
            print(f"Response: {full_resp}")
            self.assertIn("couldn't find any local records", full_resp.lower())


if __name__ == "__main__":
    unittest.main()

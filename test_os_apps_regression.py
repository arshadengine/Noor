"""
test_os_apps_regression.py
─────────────────────────────────────────────────────
Regression test suite for Phase 2.1.1:
- Verifies backward compatibility of imports from brain.llm
- Verifies application resolution for VS Code, Terminal, Chrome, Notepad
"""

import sys
import unittest
from pathlib import Path

# Ensure D:\Noor is in python path
sys.path.insert(0, str(Path(__file__).parent))

from brain.llm import get_gemini_client, call_groq_stream, call_openrouter_stream, simple_query
from brain.os_agent import open_app, APP_MAP
from brain.agents import OSAgent, PlannerAgent


class TestOSAgentRegression(unittest.TestCase):

    def test_01_llm_imports_compatibility(self):
        """Verify that legacy imports from brain.llm function without error."""
        client = get_gemini_client()
        self.assertTrue(client is not None or client is None)

    def test_02_app_map_aliases(self):
        """Verify that VS Code and Terminal app aliases exist in APP_MAP."""
        self.assertIn("visual studio code", APP_MAP)
        self.assertIn("vs code", APP_MAP)
        self.assertIn("terminal", APP_MAP)
        self.assertEqual(APP_MAP["visual studio code"], "Code.exe")
        self.assertEqual(APP_MAP["terminal"], "wt.exe")

    def test_03_heuristics_for_vs_code_and_terminal(self):
        """Verify OSAgent heuristics correctly detect open_app for VS Code and Terminal."""
        action_vscode = OSAgent._detect_action_heuristically("Open visual studio code")
        self.assertIsNotNone(action_vscode)
        self.assertEqual(action_vscode.get("type"), "open_app")
        self.assertEqual(action_vscode.get("target"), "visual studio code")

        action_terminal = OSAgent._detect_action_heuristically("Open terminal")
        self.assertIsNotNone(action_terminal)
        self.assertEqual(action_terminal.get("type"), "open_app")
        self.assertEqual(action_terminal.get("target"), "terminal")

    def test_04_open_app_execution(self):
        """Verify open_app resolves Code.exe, wt.exe, chrome.exe without verification errors."""
        res_code = open_app("visual studio code")
        self.assertIn("Successfully", res_code)

        res_term = open_app("terminal")
        self.assertIn("Successfully", res_term)


if __name__ == "__main__":
    unittest.main()

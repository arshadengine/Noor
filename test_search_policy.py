"""
test_search_policy.py
─────────────────────────────────────────────────────
Automated Acceptance Tests for Search Policy Engine, File Visibility Filter,
Developer Mode Toggle, and Structured Resolver Diagnostics.
"""

import os
import unittest
from brain.resolvers.manager import ResourceResolverManager
from brain.resolvers.base import ResourceType
from brain.tools.filesystem import find_and_rank_files, classify_file_metadata
from brain.system.workspace import toggle_developer_mode, is_developer_mode_active
from brain.os_agent import open_app


class TestSearchPolicyEngine(unittest.TestCase):

    def setUp(self):
        toggle_developer_mode(False)
        self.manager = ResourceResolverManager()

    def tearDown(self):
        toggle_developer_mode(False)

    def test_01_user_document_report(self):
        res = self.manager.classify_and_resolve("open report")
        self.assertEqual(res["resource_type"], ResourceType.FILE)
        # Verify internal audio files are excluded from user searches
        self.assertNotIn("temp_audio", res["resolved_target"])
        self.assertNotIn("response_", res["resolved_target"])

    def test_02_system_runtime_audio_excluded_in_normal_mode(self):
        meta = classify_file_metadata(r"D:\Noor\data\temp_audio\response_123.mp3", "response_123.mp3")
        self.assertEqual(meta["visibility"], "system")
        self.assertFalse(meta["searchable"])

        # Search in Normal Mode
        results_normal = find_and_rank_files("response_123.mp3", limit=5)
        self.assertFalse(any("temp_audio" in r["filepath"] for r in results_normal))

        # Search in Developer Mode
        toggle_developer_mode(True)
        self.assertTrue(is_developer_mode_active())

    def test_03_folder_downloads_resolution(self):
        res = self.manager.classify_and_resolve("open downloads folder")
        self.assertEqual(res["resource_type"], ResourceType.FOLDER)
        self.assertIn("Downloads", res["resolved_target"])

    def test_04_settings_window_resolution(self):
        res = self.manager.classify_and_resolve("open window setting")
        self.assertEqual(res["resource_type"], ResourceType.SETTINGS)
        self.assertEqual(res["resolved_target"], "ms-settings:")

    def test_05_developer_mode_toggle(self):
        self.assertFalse(is_developer_mode_active())
        toggle_developer_mode(True)
        self.assertTrue(is_developer_mode_active())
        toggle_developer_mode(False)
        self.assertFalse(is_developer_mode_active())

    def test_06_database_file_handling(self):
        result = open_app("noor.db")
        self.assertIn("SQLite database", result)

    def test_07_structured_diagnostics_logging(self):
        res = self.manager.classify_and_resolve("open github")
        self.assertIn("diagnostics", res)
        diag = res["diagnostics"]
        self.assertEqual(diag["input"], "open github")
        self.assertEqual(diag["winner"], "URLResolver")
        self.assertGreaterEqual(len(diag["candidates"]), 3)
        self.assertIn("execution_time_ms", diag)


if __name__ == "__main__":
    unittest.main()

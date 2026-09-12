"""
test_resource_resolver.py
─────────────────────────────────────────────────────
Automated Acceptance Tests for Modular ResourceResolver Pipeline.
Tests two-stage classification, confidence scoring, dev-server listening socket scanning,
and target resolution across URLs, Applications, Files, Folders, and Settings.
"""

import unittest
from brain.resolvers.manager import ResourceResolverManager
from brain.resolvers.base import ResourceType
from brain.os_agent import open_app


class TestResourceResolverPipeline(unittest.TestCase):

    def setUp(self):
        self.manager = ResourceResolverManager()

    def test_01_url_localhost(self):
        res = self.manager.classify_and_resolve("localhost")
        self.assertEqual(res["resource_type"], ResourceType.URL)
        self.assertGreaterEqual(res["confidence"], 0.85)
        self.assertTrue(res["resolved_target"].startswith("http://localhost"))

    def test_02_url_localhost_with_port(self):
        res = self.manager.classify_and_resolve("localhost:5173")
        self.assertEqual(res["resource_type"], ResourceType.URL)
        self.assertEqual(res["resolved_target"], "http://localhost:5173")
        self.assertEqual(res["confidence_tier"], "HIGH")

    def test_03_url_ipv6_loopback(self):
        res = self.manager.classify_and_resolve("::1")
        self.assertEqual(res["resource_type"], ResourceType.URL)
        self.assertTrue(res["resolved_target"].startswith("http://[::1]"))
        self.assertEqual(res["confidence_tier"], "HIGH")

    def test_04_url_lan_ip(self):
        res = self.manager.classify_and_resolve("192.168.1.20")
        self.assertEqual(res["resource_type"], ResourceType.URL)
        self.assertEqual(res["resolved_target"], "http://192.168.1.20")
        self.assertEqual(res["confidence_tier"], "HIGH")

    def test_05_url_domain_name(self):
        res = self.manager.classify_and_resolve("github.com")
        self.assertEqual(res["resource_type"], ResourceType.URL)
        self.assertEqual(res["resolved_target"], "https://github.com")
        self.assertEqual(res["confidence_tier"], "HIGH")

    def test_06_folder_downloads(self):
        res = self.manager.classify_and_resolve("Downloads")
        self.assertEqual(res["resource_type"], ResourceType.FOLDER)
        self.assertGreaterEqual(res["confidence"], 0.85)

    def test_07_settings_windows_settings(self):
        res = self.manager.classify_and_resolve("Windows Settings")
        self.assertEqual(res["resource_type"], ResourceType.SETTINGS)
        self.assertEqual(res["resolved_target"], "ms-settings:")

    def test_08_application_vs_code(self):
        res = self.manager.classify_and_resolve("Visual Studio Code")
        self.assertEqual(res["resource_type"], ResourceType.APPLICATION)
        self.assertGreaterEqual(res["confidence"], 0.85)

    def test_09_open_app_localhost_integration(self):
        result = open_app("localhost")
        self.assertIn("Opened URL in default browser", result)

    def test_10_open_github(self):
        res = self.manager.classify_and_resolve("github")
        self.assertEqual(res["resource_type"], ResourceType.URL)
        self.assertEqual(res["resolved_target"], "https://github.com")

    def test_11_open_downloads_folder(self):
        res = self.manager.classify_and_resolve("downloads folder")
        self.assertEqual(res["resource_type"], ResourceType.FOLDER)
        self.assertIn("Downloads", res["resolved_target"])

    def test_12_open_window_setting(self):
        res = self.manager.classify_and_resolve("window setting")
        self.assertEqual(res["resource_type"], ResourceType.SETTINGS)
        self.assertEqual(res["resolved_target"], "ms-settings:")


if __name__ == "__main__":
    unittest.main()

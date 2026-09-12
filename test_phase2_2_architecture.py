"""
test_phase2_2_architecture.py
─────────────────────────────────────────────────────
Automated Unit & Integration Test Suite for Phase 2.2 — Universal Tool & OS Intelligence.
"""

import sys
import os
import unittest
from pathlib import Path

# Ensure D:\Noor is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from brain.db import get_db, init_db_schema
from brain.tools.registry import ToolRegistry, RiskLevel
from brain.tools.guardrails import GuardrailPolicy
from brain.tools.filesystem import find_and_rank_files
from brain.system.monitor import get_system_state, start_system_monitor
from brain.system.discovery import scan_and_register_applications, get_application_by_query
from brain.system.workspace import set_active_workspace, get_active_workspace
from brain.knowledge.graph import add_knowledge_edge, query_knowledge_relationships


class TestPhase22UniversalIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db_schema()

    def test_01_central_database_tables(self):
        """Verify all Phase 2.2 SQLite tables exist and have valid structure."""
        with get_db() as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            self.assertIn("installed_applications", tables)
            self.assertIn("file_index", tables)
            self.assertIn("system_telemetry_logs", tables)
            self.assertIn("graph_nodes", tables)
            self.assertIn("graph_edges", tables)

    def test_02_tool_registry_and_guardrails(self):
        """Verify ToolRegistry risk levels, auto-execution, and confirmation interception."""
        # 1. Low risk auto-execution
        res_low = ToolRegistry.execute("get_system_status")
        self.assertEqual(res_low["status"], "success")

        # 2. High risk interception without confirmation
        res_high = ToolRegistry.execute("delete_file", kwargs={"path": "D:\\Noor\\test_dummy.tmp"})
        self.assertEqual(res_high["status"], "confirmation_required")
        self.assertIn("impact_summary", res_high)
        self.assertIn("Warning", res_high["impact_summary"])

        # 3. High risk execution with explicit confirmation
        res_confirmed = ToolRegistry.execute("delete_file", kwargs={"path": "D:\\Noor\\nonexistent.tmp"}, confirmed=True)
        self.assertEqual(res_confirmed["status"], "success")

    def test_03_app_discovery_and_intent_synonyms(self):
        """Verify app scanning and multi-tag synonym resolution (IDE -> VS Code, Browser -> Chrome/Brave)."""
        count = scan_and_register_applications(force_refresh=True)
        self.assertGreater(count, 0)

        app_ide = get_application_by_query("Launch my IDE")
        self.assertIsNotNone(app_ide)
        self.assertEqual(app_ide["category"].lower(), "ide")

        app_browser = get_application_by_query("Open my browser")
        self.assertIsNotNone(app_browser)
        self.assertTrue("chrome" in app_browser["name"].lower() or "brave" in app_browser["name"].lower() or "edge" in app_browser["name"].lower())

    def test_04_multi_factor_file_ranking(self):
        """Verify 4-factor file ranking prioritizing active workspace and recent files."""
        set_active_workspace("D:\\Noor")
        matches = find_and_rank_files("agents", active_workspace=get_active_workspace(), limit=5)
        self.assertTrue(len(matches) > 0)
        top = matches[0]
        self.assertIn("rank_score", top)
        self.assertIn("agents", top["filename"].lower())

    def test_05_event_driven_system_monitor(self):
        """Verify background hardware monitor returns real-time CPU, RAM, Battery, and active window info."""
        start_system_monitor()
        state = get_system_state()
        self.assertIn("cpu_percent", state)
        self.assertIn("ram_percent", state)
        self.assertIn("battery", state)
        self.assertIn("active_app", state)

    def test_06_knowledge_graph_relationships(self):
        """Verify storing and querying entity edges in OS Knowledge Graph."""
        add_knowledge_edge("VS Code", "Application", "OPENED", "D:\\Noor", "Project")
        rels = query_knowledge_relationships("VS Code")
        self.assertTrue(len(rels) > 0)
        edge = rels[0]
        self.assertIn("VS Code", edge["source_name"])
        self.assertEqual(edge["relation"], "OPENED")
        self.assertIn("D:\\Noor", edge["target_name"])


if __name__ == "__main__":
    unittest.main()

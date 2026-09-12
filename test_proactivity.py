"""
test_proactivity.py
─────────────────────────────────────────────────────
Unit tests for Phase 2 Proactive Daemon sensors and reasoning.
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))

from brain.memory import init_db, get_unread_proactive_suggestions, _get_db
from brain.proactive_daemon import (
    check_new_downloads, check_clipboard_changes, check_active_workspace,
    _seen_downloads, _last_clipboard_text, _current_active_workspace
)

class TestProactiveDaemon(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ensure database is initialized
        init_db()
        
    def setUp(self):
        # Clear proactive suggestions table before each test
        with _get_db() as conn:
            conn.execute("DELETE FROM proactive_suggestions")
            conn.execute("DELETE FROM preferences")
            
        # Reset daemon memory states
        _seen_downloads.clear()
        global _last_clipboard_text, _current_active_workspace
        import brain.proactive_daemon
        brain.proactive_daemon._last_clipboard_text = ""
        brain.proactive_daemon._current_active_workspace = ""
        
        # Setup temporary downloads folder
        self.temp_downloads = Path(__file__).parent / "temp_test_downloads"
        self.temp_downloads.mkdir(exist_ok=True)

    def tearDown(self):
        # Clean up temporary downloads
        if self.temp_downloads.exists():
            shutil.rmtree(self.temp_downloads)

    def test_1_downloads_monitor(self):
        print("\n--- Running Test: Downloads Monitor ---")
        
        # 1. Seed existing downloads
        test_file_old = self.temp_downloads / "old_doc.txt"
        test_file_old.write_text("This is an old document content.")
        _seen_downloads.add(str(test_file_old.resolve()))
        
        # 2. Add a new file
        test_file_new = self.temp_downloads / "new_report.txt"
        test_file_new.write_text("Project Noor update: Phase 2 includes background proactivity and context awareness. This is the new architecture report.")
        
        # 3. Trigger Downloads Watcher
        check_new_downloads(self.temp_downloads)
        
        # 4. Verify suggestion in database
        suggestions = get_unread_proactive_suggestions()
        print(f"Suggestions found: {len(suggestions)}")
        self.assertTrue(len(suggestions) > 0, "No proactive suggestion was generated for the new file.")
        
        suggestion = suggestions[0]
        print(f"Title: {suggestion['title']}")
        print(f"Content: {suggestion['content']}")
        self.assertIn("New Document Downloaded", suggestion["title"])
        self.assertEqual(suggestion["event_type"], "download")
        self.assertEqual(suggestion["action_data"]["filename"], "new_report.txt")

    @patch("brain.proactive_daemon.get_clipboard_text")
    def test_2_clipboard_monitor(self, mock_get_clip):
        print("\n--- Running Test: Clipboard Monitor ---")
        
        # Mock copying a python function
        mock_code = (
            "def calculate_sum(a, b):\n"
            "    # This is a sample code block\n"
            "    result = a + b\n"
            "    return result\n"
        )
        mock_get_clip.return_value = mock_code
        
        # Trigger Clipboard Watcher
        check_clipboard_changes()
        
        # Verify suggestion in database
        suggestions = get_unread_proactive_suggestions()
        print(f"Suggestions found: {len(suggestions)}")
        self.assertTrue(len(suggestions) > 0, "No proactive suggestion was generated for the copied code.")
        
        suggestion = suggestions[0]
        print(f"Title: {suggestion['title']}")
        print(f"Content: {suggestion['content']}")
        self.assertEqual(suggestion["title"], "Code Copied to Clipboard")
        self.assertEqual(suggestion["event_type"], "clipboard")
        self.assertEqual(suggestion["action_data"]["text"], mock_code)

    @patch("brain.proactive_daemon.get_focused_app_and_title")
    def test_3_workspace_monitor(self, mock_focus):
        print("\n--- Running Test: Workspace Monitor ---")
        
        # Mock active window to be VS Code with Noor project open
        mock_focus.return_value = {
            "title": "main.py - Noor - Visual Studio Code",
            "app": "Code.exe"
        }
        
        # Trigger Workspace Watcher
        check_active_workspace()
        
        # Verify suggestion in database
        suggestions = get_unread_proactive_suggestions()
        print(f"Suggestions found: {len(suggestions)}")
        self.assertTrue(len(suggestions) > 0, "No proactive suggestion was generated for workspace focus.")
        
        suggestion = suggestions[0]
        print(f"Title: {suggestion['title']}")
        print(f"Content: {suggestion['content']}")
        self.assertEqual(suggestion["title"], "Noor Workspace Loaded")
        self.assertEqual(suggestion["event_type"], "workspace")
        self.assertEqual(suggestion["action_data"]["workspace_path"], "D:/Noor")


if __name__ == "__main__":
    unittest.main()

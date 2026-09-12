"""
brain/planner/templates/__init__.py
─────────────────────────────────────────────────────
Modular Template Registry for TaskPlanner.
Imports templates for open, coding, search, browser, and system plans.
"""

from brain.planner.templates.open import get_open_template
from brain.planner.templates.coding import get_coding_template
from brain.planner.templates.search import get_search_template
from brain.planner.templates.browser import get_browser_template
from brain.planner.templates.system import get_system_template

__all__ = [
    "get_open_template",
    "get_coding_template",
    "get_search_template",
    "get_browser_template",
    "get_system_template",
]

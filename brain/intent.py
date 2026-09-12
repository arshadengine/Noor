"""
brain/intent.py
─────────────────────────────────────────────────────
Stage 1: Intent Classification & Internal Subsystem Router for Noor.

Classifies incoming prompts into task categories and dispatches directly to
Noor's internal OS Agent, Vision Agent, Memory Engine, or Search Agent when an
LLM model selection is not required.
"""

from __future__ import annotations
import re
from typing import Any


def classify_intent(message: str) -> tuple[str, dict[str, Any]]:
    """
    Classify incoming prompt into a task category and extract required model constraints.
    """
    msg_lower = message.lower().strip()
    required_constraints: dict[str, Any] = {}

    # Check for Vision / Image Attachment
    if "🖼️ [attached image]:" in msg_lower or "attached image:" in msg_lower or "describe this image" in msg_lower:
        required_constraints["vision"] = True
        return "VISION", required_constraints

    # Check OS Control
    os_keywords = [
        "open ", "launch ", "close ", "screenshot", "system info", "cpu", "ram", "disk",
        "shutdown", "restart", "volume", "mute", "brightness", "explorer", "vs code", "chrome"
    ]
    if any(k in msg_lower for k in os_keywords):
        return "OS_CONTROL", required_constraints

    # Check Memory / Historical Query
    memory_keywords = [
        "what did i tell you", "what file did i edit", "what project did i", "yesterday",
        "remember when", "my preference", "last time", "history", "records"
    ]
    if any(k in msg_lower for k in memory_keywords):
        return "MEMORY", required_constraints

    # Check Coding & Debugging
    code_keywords = [
        "code", "python", "javascript", "c++", "rust", "function", "class", "script",
        "react", "fastapi", "flask", "bug", "traceback", "syntax", "refactor"
    ]
    if any(k in msg_lower for k in code_keywords):
        if any(dk in msg_lower for dk in ["fix", "error", "bug", "traceback", "debug", "failed"]):
            return "DEBUGGING", required_constraints
        return "CODING", required_constraints

    # Check Research & Search
    search_keywords = ["search", "latest news", "find online", "who won", "current weather", "web search"]
    if any(k in msg_lower for k in search_keywords):
        return "RESEARCH", required_constraints

    # Check Planning
    planning_keywords = ["plan", "roadmap", "schedule", "milestone", "strategy", "architecture", "step by step"]
    if any(k in msg_lower for k in planning_keywords):
        return "PLANNING", required_constraints

    # Check Reasoning & Science
    reasoning_keywords = [
        "calculate", "solve", "math", "equation", "proof", "quantum", "physics",
        "explain", "recursion", "why does", "concept of", "theory", "derive", "logic"
    ]
    if any(k in msg_lower for k in reasoning_keywords):
        return "REASONING", required_constraints

    # Default to Casual Chat
    return "CHAT", required_constraints

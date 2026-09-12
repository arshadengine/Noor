"""
brain/personality.py
─────────────────────────────────────────────────────
Noor's Personality Engine.

Responsibilities:
  1. Load the personality/system prompt from personality.txt
  2. Detect which MODE is most appropriate for a given user message
  3. Build the final system prompt injected into every LLM call
"""

from __future__ import annotations

import os
import re
import datetime
from pathlib import Path
from dotenv import load_dotenv


load_dotenv(Path(__file__).parent.parent / ".env")

PERSONALITY_PATH = Path(os.getenv("PERSONALITY_PATH", "D:/Noor/configs/personality.txt"))

# ──────────────────────────────────────────────────────────────────────────────
# Mode detection keywords
# ──────────────────────────────────────────────────────────────────────────────
_MODE_KEYWORDS: dict[str, list[str]] = {
    "coder": [
        r"\bcode\b", r"\bfunction\b", r"\bclass\b", r"\bdebug\b", r"\berror\b",
        r"\bexception\b", r"\bpython\b", r"\bjavascript\b", r"\bsql\b",
        r"\bgit\b", r"\bimport\b", r"\binstall\b", r"\bpip\b", r"\bapi\b",
        r"\bscript\b", r"\bfastapi\b", r"\bfixing?\b", r"\brefactor\b",
    ],
    "researcher": [
        r"\bpaper\b", r"\bresearch\b", r"\bstudy\b", r"\bscientific\b",
        r"\bliterature\b", r"\bjournal\b", r"\btheory\b", r"\bhypothesis\b",
        r"\bexplain\b", r"\bwhat is\b", r"\bhow does\b", r"\bwhy does\b",
        r"\bpublished\b", r"\bstatistics?\b", r"\bdata\b", r"\banalysis\b",
    ],
    "mentor": [
        r"\bgoal\b", r"\bcareer\b", r"\bplan\b", r"\bhabits?\b", r"\badvice\b",
        r"\bstrategy\b", r"\bpriority\b", r"\bsuccess\b", r"\bfailure\b",
        r"\bimprove\b", r"\bprogress\b", r"\bdecision\b", r"\bshould i\b",
        r"\bwhat should\b", r"\bstartup\b", r"\bproject\b", r"\bdeadline\b",
    ],
    "os": [
        r"\bopen notepad\b", r"\bopen calculator\b", r"\bopen paint\b", r"\bopen explorer\b",
        r"\bopen cmd\b", r"\bopen command prompt\b", r"\bopen powershell\b",
        r"\bdisk space\b", r"\bfree space\b", r"\bdrive space\b", r"\bspace khali\b", r"\bspace free\b",
        r"\bkhali space\b", r"\bkitna space\b", r"\bdisk usage\b",
        r"\bclipboard\b", r"\bclip\b",
        r"\bclose notepad\b", r"\bclose calculator\b", r"\bclose paint\b", r"\bclose chrome\b", r"\bclose brave\b", r"\bclose app\b",
        r"\bswitch to\b", r"\bswitch window\b", r"\bbring to foreground\b",
        r"\bcreate file\b", r"\bwrite file\b", r"\bsave file\b", r"\bdelete file\b", r"\bedit file\b", r"\bread file\b", r"\bopen folder\b", r"\bopen project\b",
        r"\bopen settings\b", r"\bsettings app\b", r"\bbluetooth\b", r"\bwi-?fi\b", r"\bnetwork settings\b",
        r"\btake screenshot\b", r"\bscreenshot\b", r"\bscreen shot\b", r"\bscreen capture\b",
        r"\bairplane mode\b", r"\bairplane\b", r"\bturn on\b", r"\bturn off\b", r"\benable\b", r"\bdisable\b", r"\btoggle\b",
        r"\bhow many files\b", r"\bfiles in\b", r"\blist files\b", r"\blist folder\b", r"\bcontents of\b", r"\bdir\b", r"\bls\b", r"\bshow files\b",
        r"\bdelete\b", r"\bremove\b",
        r"\bappend\b", r"\bedit\b",
        r"\bwhat is in\b.*\bfolder\b", r"\bwhat's in\b.*\bfolder\b", r"\bcheck\b.*\bfolder\b", r"\bwhat is inside\b", r"\bwhat's inside\b", r"\bwhats inside\b", r"\bwhats in\b", r"\bwhats inside\b.*\bfolder\b",
        r"^\s*in\s+[\w\-]+\??\s*$",
        r"^\s*inside\s+[\w\-]+\??\s*$",
        r"^\s*in\s+this\??\s*$",
        r"^\s*in\s+it\??\s*$",
        r"\b(?:folder|directory|files?|path)\s+(?:mein|me|kya|hai|hain)\b",
        r"\b(?:mein|me|kya|hai|hain)\s+(?:folder|directory|files?|path)\b",
        r"\b[\w\-]+\s+folder\s+mein\b",
        r"\b[\w\-]+\s+folder\s+me\b",
        r'"[\w\-]+"\s+folder',
        r"'[\w\-]+'\s+folder"
    ],
    "vision": [
        r"\battached image\b", r"\bdescribe my screen\b", r"\bdescribe the screen\b", r"\bsee my screen\b", r"\bwhat's on my screen\b", r"\bwhat is on my screen\b"
    ]
}

_MODE_ADDONS: dict[str, str] = {
    "friend": (
        "You are in FRIEND MODE. Be relaxed, warm, and conversational. "
        "Keep responses concise and natural."
    ),
    "mentor": (
        "You are in MENTOR MODE. Be constructive, goal-oriented, and honest. "
        "Help Arshad make good decisions and take meaningful actions."
    ),
    "researcher": (
        "You are in RESEARCHER MODE. Be precise and evidence-based. "
        "Break down complex ideas clearly. Cite reasoning when needed."
    ),
    "coder": (
        "You are in CODER MODE. Be technical and efficient. "
        "Prefer working, minimal code over long explanations. "
        "Include comments for non-obvious logic."
    ),
    "os": (
        "You are in OS MODE. You can run commands on the system, list files/folders, and access clipboard or settings. "
        "Explain what action was taken clearly and concisely."
    ),
    "vision": (
        "You are in VISION MODE. You can see screenshots or attached images. "
        "Describe what is visual on the screen or image and answer the user's questions about it."
    ),
}


def detect_mode(message: str) -> str:
    """Return the most appropriate mode for the given user message."""
    msg_lower = message.lower()
    scores: dict[str, int] = {m: 0 for m in _MODE_KEYWORDS.keys()}
    scores["friend"] = 0

    for mode, patterns in _MODE_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                scores[mode] += 1

    best_mode = max(scores, key=lambda m: scores[m])
    # Only switch from friend if there's a clear signal
    return best_mode if scores[best_mode] > 0 else "friend"


def build_system_prompt(
    mode: str,
    memories: list[str] | None = None,
) -> str:
    """
    Build the complete system prompt for an LLM call.

    Args:
        mode: One of 'friend', 'mentor', 'researcher', 'coder', 'os', 'vision'
        memories: List of relevant memory strings to inject
    """
    # Load base personality
    try:
        base = PERSONALITY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        base = "You are Noor, Arshad's personal AI companion."

    # Add mode-specific instructions
    mode_text = _MODE_ADDONS.get(mode, _MODE_ADDONS["friend"])

    # Build memory block
    memory_block = ""
    if memories:
        joined = "\n".join(f"  - {m}" for m in memories[:10])
        memory_block = (
            f"\n\n------------------------------------------\n"
            f"RELEVANT MEMORIES (use naturally if helpful)\n"
            f"------------------------------------------\n"
            f"{joined}"
        )

    # Inject current date, time, and day of week
    now = datetime.datetime.now()
    time_str = now.strftime("%A, %B %d, %Y, %I:%M %p")
    time_block = f"\n\n[CURRENT DATE & TIME]\n- Date/Time: {time_str}\n"

    return f"{base}{time_block}\n[CURRENT MODE]\n{mode_text}{memory_block}"


def get_mode_emoji(mode: str) -> str:
    return {
        "friend": "😊",
        "mentor": "🎯",
        "researcher": "🔬",
        "coder": "💻",
        "os": "🖥️",
        "vision": "👁️"
    }.get(mode, "😊")

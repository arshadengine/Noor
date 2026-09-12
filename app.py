"""
app.py — Entrypoint for Cloud & Hugging Face Spaces Hosting
────────────────────────────────────────────────────────────
Enables 1-click deployment on Hugging Face Spaces, Render, and cloud VMs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

# Ensure required runtime folders exist
for folder in ["data", "chroma_db", "knowledge"]:
    (ROOT_DIR / folder).mkdir(parents=True, exist_ok=True)

# Initialize database schema
try:
    from brain.memory import init_db
    init_db()
except Exception as e:
    print(f"[Noor Cloud] Database initialization notice: {e}")

# Build UI
from ui.chat_ui import build_ui

demo = build_ui()

if __name__ == "__main__":
    host = os.getenv("HOST", os.getenv("UI_HOST", "0.0.0.0"))
    port = int(os.getenv("PORT", os.getenv("UI_PORT", "7860")))
    print(f"[Noor] Launching cloud interface on http://{host}:{port} ...")
    demo.launch(
        server_name=host,
        server_port=port,
        show_error=True,
    )

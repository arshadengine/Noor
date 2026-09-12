"""
main.py
─────────────────────────────────────────────────────
Noor — Phase 1 Entry Point.

Starts both the FastAPI backend and Gradio UI concurrently.

Usage:
    python main.py

Access:
    Chat UI  →  http://localhost:7860
    API      →  http://localhost:8000
    API Docs →  http://localhost:8000/docs
"""

from __future__ import annotations

import os
import sys
import time
import threading
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

# Load .env before anything else
load_dotenv(Path(__file__).parent / ".env")

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
UI_HOST  = os.getenv("UI_HOST", "127.0.0.1")
UI_PORT  = int(os.getenv("UI_PORT", "7860"))

FAST_MODEL = os.getenv("NOOR_FAST_MODEL", "qwen2.5-coder:latest")
HEAVY_MODEL = os.getenv("NOOR_HEAVY_MODEL", "gemma4:latest")
CODER_MODEL = os.getenv("NOOR_CODER_MODEL", "qwen2.5-coder:latest")


def print_banner() -> None:
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY", ""))
    has_gemini = bool(os.getenv("GEMINI_API_KEY", ""))
    
    if has_openrouter:
        model_status = f"Active via OpenRouter ({os.getenv('OPENROUTER_MODEL', 'google/gemini-2.0-flash')})"
    elif has_gemini:
        model_status = f"Active via Direct Gemini ({os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')})"
    else:
        model_status = "Inactive (Using local Ollama)"
        
    banner = f"""
+======================================================+
|                                                      |
|   * N O O R  -- Personal AI Companion                |
|     Phase 1 - Foundation Layer                       |
|                                                      |
|   Chat UI  ->  http://{UI_HOST}:{UI_PORT}              |
|   REST API ->  http://{API_HOST}:{API_PORT}              |
|   API Docs ->  http://{API_HOST}:{API_PORT}/docs         |
|                                                      |
|   Model (Cloud/Gemini): {model_status}
|   Model (Fast Chat)   : {FAST_MODEL}
|   Model (Heavy Reason): {HEAVY_MODEL}
|   Model (Coder)       : {CODER_MODEL}
|   Memory              : SQLite + ChromaDB                 |
|                                                      |
|   Press Ctrl+C to stop.                              |
+======================================================+
"""
    print(banner)


def start_api() -> None:
    """Start the FastAPI server in a background thread."""
    import uvicorn
    from api.server import app
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="warning",
    )


def start_ui() -> None:
    """Start the Gradio UI (blocking main thread)."""
    from ui.chat_ui import launch
    launch()


def check_dependencies() -> bool:
    """Quick sanity check before starting."""
    missing = []
    for pkg in ["ollama", "chromadb", "fastapi", "gradio", "dotenv"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt\n")
        return False

    # Check Ollama
    try:
        import ollama
        models = ollama.list()
        model_names = [m.model for m in models.models]
        print(f"[Noor] ✅ Ollama connected. Models: {', '.join(model_names)}")
    except Exception as e:
        print(f"[Noor] ⚠️  Ollama not reachable: {e}")
        print("[Noor]    Start Ollama with: ollama serve")

    return True


def main() -> None:
    print_banner()

    if not check_dependencies():
        sys.exit(1)

    # Initialize the database
    from brain.memory import init_db
    init_db()

    # Start Proactive Daemon
    try:
        from brain.proactive_daemon import start_proactive_daemon
        start_proactive_daemon()
    except Exception as e:
        print(f"[Noor] Failed to start proactive daemon: {e}")

    # Start API in background thread
    api_thread = threading.Thread(target=start_api, daemon=True, name="NoorAPI")
    api_thread.start()
    time.sleep(1.5)  # Give API a moment to bind
    print(f"[Noor] API running at http://{API_HOST}:{API_PORT}")

    # Start UI (blocks)
    print(f"[Noor] Starting Chat UI at http://{UI_HOST}:{UI_PORT} ...")
    start_ui()


if __name__ == "__main__":
    main()

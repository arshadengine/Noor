"""
ui/chat_ui.py
─────────────────────────────────────────────────────
Noor's Gradio Chat Interface.

Features:
  - Dark-themed premium chat UI
  - Mode indicator (Friend / Mentor / Researcher / Coder)
  - Memory sidebar showing what Noor knows about you
  - File upload for knowledge ingestion
  - Session management
"""

from __future__ import annotations

import os
import sys
import uuid
import re
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv(Path(__file__).parent.parent / ".env")

from brain.llm import chat, check_ollama
from brain.memory import (
    get_all_memories, init_db, get_session_previews, 
    get_session_history_for_ui, get_graph_summary, get_recent_agent_logs,
    add_automation_task, get_automation_tasks, delete_automation_task
)
from brain.personality import detect_mode, get_mode_emoji
from brain.voice import speak_text, transcribe_audio


try:
    from brain.embeddings import embed, chunk_and_embed
    from brain.memory import ingest_chunks
    EMBEDDINGS_AVAILABLE = True
except Exception:
    EMBEDDINGS_AVAILABLE = False

UI_HOST = os.getenv("UI_HOST", "127.0.0.1")
UI_PORT = int(os.getenv("UI_PORT", "7860"))

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Dark premium theme
# ─────────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; box-sizing: border-box; }

:root {
    --bg-primary:   #0d0f12;
    --bg-secondary: #141720;
    --bg-card:      #1a1e2a;
    --bg-input:     #1e2330;
    --accent:       #7c6af7;
    --accent-light: #9d8fff;
    --accent-glow:  rgba(124, 106, 247, 0.25);
    --text-primary: #e8eaf0;
    --text-muted:   #6b7280;
    --border:       #252a38;
    --success:      #34d399;
    --warning:      #fbbf24;
}

body, .gradio-container {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* Header */
.noor-header {
    background: linear-gradient(135deg, #1a1e2a 0%, #0d0f12 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 28px;
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 0;
}
.noor-logo {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, var(--accent) 0%, #a78bfa 100%);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    box-shadow: 0 0 20px var(--accent-glow);
}
.noor-title { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.noor-subtitle { font-size: 12px; color: var(--text-muted); }

/* Mode badge */
.mode-badge {
    margin-left: auto;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    background: var(--accent-glow);
    border: 1px solid var(--accent);
    color: var(--accent-light);
}

/* Chat */
.chatbot { background: var(--bg-secondary) !important; border: 1px solid var(--border) !important; border-radius: 16px !important; }
.chatbot .message { border-radius: 12px !important; }
.chatbot .message.user { background: var(--accent-glow) !important; border: 1px solid var(--accent) !important; }
.chatbot .message.bot { background: var(--bg-card) !important; border: 1px solid var(--border) !important; }

/* Input */
.input-row { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 14px !important; padding: 8px !important; }
textarea, input[type="text"] {
    background: transparent !important;
    border: none !important;
    color: var(--text-primary) !important;
    font-size: 15px !important;
}
textarea:focus, input:focus { outline: none !important; box-shadow: none !important; }

/* Buttons */
button.primary-btn {
    background: linear-gradient(135deg, var(--accent) 0%, #6d56e8 100%) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important;
    padding: 10px 22px !important;
    box-shadow: 0 4px 15px var(--accent-glow) !important;
    transition: all 0.2s ease !important;
}
button.primary-btn:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 20px var(--accent-glow) !important; }

/* Sidebar */
.memory-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px;
}
.memory-item {
    padding: 8px 12px;
    margin: 4px 0;
    background: var(--bg-input);
    border-radius: 8px;
    font-size: 13px;
    border-left: 3px solid var(--accent);
    color: var(--text-primary);
}

/* Tabs */
.tabs { background: var(--bg-secondary) !important; border: 1px solid var(--border) !important; border-radius: 16px !important; }
.tab-nav button { color: var(--text-muted) !important; }
.tab-nav button.selected { color: var(--accent-light) !important; border-bottom: 2px solid var(--accent) !important; }

/* Status bar */
.status-bar {
    font-size: 12px; color: var(--text-muted);
    padding: 6px 16px;
    display: flex; gap: 16px;
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); display: inline-block; margin-right: 6px; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_memories_text() -> str:
    """Format memories for display in the sidebar."""
    mems = get_all_memories(limit=20)
    if not mems:
        return "No memories yet. Start chatting with Noor!"
    lines = []
    for m in mems:
        star = "⭐" * m["importance"]
        lines.append(f"{star} {m['content']}")
    return "\n\n".join(lines)


def get_agent_logs_text() -> str:
    """Format recent agent logs for the UI."""
    logs = get_recent_agent_logs(limit=15)
    if not logs:
        return "No agent actions logged yet."
    lines = []
    for l in logs:
        try:
            t = l["timestamp"].split("T")[1].split(".")[0]
        except Exception:
            t = l["timestamp"]
        res_str = f" => {l['result']}" if l['result'] else ""
        lines.append(f"[{t}] [{l['agent_name']}] {l['action']}{res_str}")
    return "\n".join(lines)


def get_tasks_summary_text() -> str:
    """Format automation tasks for display in the UI."""
    try:
        tasks = get_automation_tasks()
        if not tasks:
            return "No scheduled automation tasks yet."
        lines = []
        for t in tasks:
            trigger_info = ""
            if t["interval_seconds"]:
                trigger_info = f"every {t['interval_seconds']} seconds"
            elif t["trigger_time"]:
                trigger_info = f"daily at {t['trigger_time']} UTC"
            else:
                trigger_info = "manual"
            
            last_run = t["last_run"] or "never"
            status_emoji = "🟢" if t["status"] == "active" else "🟡"
            lines.append(
                f"ID: {t['id']} | {status_emoji} {t['task_description']}\n"
                f"   Trigger: {trigger_info} | Last Run: {last_run}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error retrieving tasks: {e}"


def add_task_ui(description: str, trigger_type: str, value_str: str) -> tuple[str, str]:
    if not description.strip():
        return "❌ Task description cannot be empty.", get_tasks_summary_text()
    
    try:
        if trigger_type == "Interval (Seconds)":
            interval = int(value_str.strip())
            task_id = add_automation_task(description.strip(), interval_seconds=interval)
            return f"✅ Task {task_id} scheduled successfully.", get_tasks_summary_text()
        else:
            time_str = value_str.strip()
            # Basic validation of HH:MM
            if not re.match(r"^\d{2}:\d{2}$", time_str):
                return "❌ Invalid time format. Must be HH:MM (24-hour style, e.g. 14:30).", get_tasks_summary_text()
            task_id = add_automation_task(description.strip(), trigger_time=time_str)
            return f"✅ Task {task_id} scheduled successfully.", get_tasks_summary_text()
    except ValueError:
        return "❌ Invalid value. For Interval, please enter a valid integer number of seconds.", get_tasks_summary_text()
    except Exception as e:
        return f"❌ Failed to schedule task: {e}", get_tasks_summary_text()


def delete_task_ui(task_id) -> tuple[str, str]:
    if task_id is None:
        return "❌ Please enter a valid Task ID.", get_tasks_summary_text()
    
    try:
        delete_automation_task(int(task_id))
        return f"✅ Task {int(task_id)} deleted successfully.", get_tasks_summary_text()
    except Exception as e:
        return f"❌ Failed to delete task: {e}", get_tasks_summary_text()


def get_proactive_suggestions_text() -> str:
    """Retrieve and format unread proactive suggestions."""
    from datetime import datetime
    try:
        from brain.memory import get_unread_proactive_suggestions
        suggestions = get_unread_proactive_suggestions(limit=15)
        if not suggestions:
            return "✨ No new alerts or insights. Noor is monitoring Downloads, Clipboard, and Workspaces in the background..."
        
        lines = []
        for s in suggestions:
            try:
                created_dt = datetime.fromisoformat(s["created_at"])
                time_str = created_dt.strftime("%H:%M:%S")
            except Exception:
                time_str = s["created_at"]
            lines.append(f"🔔 [{time_str}] {s['title']}")
            lines.append(f"{s['content']}")
            lines.append("-" * 40)
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error retrieving suggestions: {e}"


def clear_proactive_suggestions() -> tuple[str, str]:
    """Clear all unread proactive suggestions by marking them as read."""
    try:
        from brain.memory import get_unread_proactive_suggestions, mark_proactive_suggestion_status
        suggestions = get_unread_proactive_suggestions(limit=100)
        for s in suggestions:
            mark_proactive_suggestion_status(s["id"], "read")
        return "✅ Cleared all alerts.", get_proactive_suggestions_text()
    except Exception as e:
        return f"❌ Failed to clear alerts: {e}", get_proactive_suggestions_text()


def take_screenshot_ui(history, session_id, mode_display, voice_enabled):
    from brain.vision import take_screenshot
    filepath = take_screenshot()
    if filepath.startswith("❌"):
        history = list(history) + [{"role": "assistant", "content": filepath}]
        yield history, mode_display, session_id, get_memories_text(), gr.update(), None
        return
    
    # Now trigger respond stream
    message = "Describe my screen."
    for outputs in respond(message, history, session_id, mode_display, voice_enabled, filepath):
        yield outputs


def quick_action_ui(action_text, history, session_id, mode_display, voice_enabled):
    for outputs in respond(action_text, history, session_id, mode_display, voice_enabled):
        yield outputs


def open_browser_ui(history, session_id, mode_display, voice_enabled):
    for outputs in respond("Open browser", history, session_id, mode_display, voice_enabled):
        yield outputs


def open_notepad_ui(history, session_id, mode_display, voice_enabled):
    for outputs in respond("Open notepad", history, session_id, mode_display, voice_enabled):
        yield outputs


def read_clipboard_ui(history, session_id, mode_display, voice_enabled):
    for outputs in respond("Read clipboard contents", history, session_id, mode_display, voice_enabled):
        yield outputs


def active_window_ui(history, session_id, mode_display, voice_enabled):
    for outputs in respond("What is the active window title?", history, session_id, mode_display, voice_enabled):
        yield outputs


def respond(
    message: str,
    history: list,
    session_id: str,
    mode_display: str,
    voice_enabled: bool = False,
    image_file: str = None,
):
    """Handle a chat message and stream the response."""
    if not message.strip() and not image_file:
        yield history, mode_display, session_id, get_memories_text(), gr.update(), None
        return

    if not session_id:
        session_id = str(uuid.uuid4())

    # Build full message with image attachment notation if present
    if image_file:
        full_message = f"🖼️ [Attached Image]: {image_file}\n{message}"
    else:
        full_message = message

    # Detect mode for display
    mode = detect_mode(full_message)
    emoji = get_mode_emoji(mode)
    new_mode_display = f"{emoji} {mode.capitalize()} Mode"

    # Add user message to history immediately
    history = list(history) + [{"role": "user", "content": full_message}]
    
    # Refresh dropdown choices at start
    previews = get_session_previews()
    choices = [(f"{p['preview'][:30]}... ({p['msg_count']} msgs)", p["session_id"]) for p in previews]
    dropdown_update = gr.update(choices=choices, value=session_id)
    yield history, new_mode_display, session_id, get_memories_text(), dropdown_update, None

    # Stream response
    partial = ""
    history = list(history) + [{"role": "assistant", "content": ""}]
    for token, actual_mode in chat(full_message, session_id, stream=True):
        partial += token
        history[-1]["content"] = partial
        emoji = get_mode_emoji(actual_mode)
        new_mode_display = f"{emoji} {actual_mode.capitalize()} Mode"
        yield history, new_mode_display, session_id, get_memories_text(), gr.update(), None

    # Final yield with complete response, updated memories, refreshed dropdown, and audio reply if voice is enabled
    previews = get_session_previews()
    choices = [(f"{p['preview'][:30]}... ({p['msg_count']} msgs)", p["session_id"]) for p in previews]
    dropdown_update = gr.update(choices=choices, value=session_id)
    
    audio_reply = None
    if voice_enabled and partial and not partial.startswith("⚠️ [Noor Error]"):
        try:
            audio_reply = speak_text(partial)
        except Exception as err:
            print(f"[Noor Voice] Failed to generate audio reply: {err}")
            
    yield history, new_mode_display, session_id, get_memories_text(), dropdown_update, audio_reply


def clear_chat(session_id: str):
    """Clear the chat history (start a new session)."""
    new_session = str(uuid.uuid4())
    previews = get_session_previews()
    choices = [(f"{p['preview'][:30]}... ({p['msg_count']} msgs)", p["session_id"]) for p in previews]
    return [], new_session, "😊 Friend Mode", get_memories_text(), gr.update(choices=choices, value=None)


def start_new_chat():
    """Clear chatbot and generate a new session ID, keeping dropdown choices."""
    new_session = str(uuid.uuid4())
    return [], new_session, "😊 Friend Mode", get_memories_text(), gr.update(value=None)


def load_session(selected_session_id: str):
    """Load session history and update session ID state."""
    if not selected_session_id:
        return [], "", "😊 Friend Mode", get_memories_text()
    
    # Fetch history
    history = get_session_history_for_ui(selected_session_id)
    
    # Detect mode of last user message
    mode_display = "😊 Friend Mode"
    if history:
        last_user = next((m for m in reversed(history) if m["role"] == "user"), None)
        if last_user:
            mode = last_user.get("mode") or detect_mode(last_user["content"])
            emoji = get_mode_emoji(mode)
            mode_display = f"{emoji} {mode.capitalize()} Mode"
            
    return history, selected_session_id, mode_display, get_memories_text()


def on_load_ui():
    """Populate session history dropdown choices on page load."""
    previews = get_session_previews()
    choices = [(f"{p['preview'][:30]}... ({p['msg_count']} msgs)", p["session_id"]) for p in previews]
    return gr.update(choices=choices, value=None)


def process_voice_input(
    audio_path: str,
    history: list,
    session_id: str,
    mode_display: str,
    voice_enabled: bool,
):
    """Process an audio query from the microphone input."""
    if not audio_path:
        yield history, mode_display, session_id, get_memories_text(), gr.update(), None
        return
        
    # Transcribe audio using STT
    text = transcribe_audio(audio_path)
    if not text.strip():
        # Display an explanation bubble in chat
        history = list(history) + [
            {"role": "user", "content": "🎙️ [Audio Query]"}, 
            {"role": "assistant", "content": "I couldn't quite hear that. Could you please check your microphone and speak again?"}
        ]
        yield history, mode_display, session_id, get_memories_text(), gr.update(), None
        return

    # Add user message transcription to chatbot history immediately
    history = list(history) + [{"role": "user", "content": f"🎙️ (Voice Query): {text}"}]
    
    # Refresh dropdown choices at start
    previews = get_session_previews()
    choices = [(f"{p['preview'][:30]}... ({p['msg_count']} msgs)", p["session_id"]) for p in previews]
    dropdown_update = gr.update(choices=choices, value=session_id)
    yield history, mode_display, session_id, get_memories_text(), dropdown_update, None

    # Call the core chat response and stream
    final_history = history
    final_mode = mode_display
    final_session = session_id
    final_memories = get_memories_text()
    final_dropdown = dropdown_update
    
    # Save user message to memory
    if not final_session:
        final_session = str(uuid.uuid4())
        
    partial = ""
    final_history = list(final_history) + [{"role": "assistant", "content": ""}]
    
    try:
        # Stream response
        for token, mode in chat(text, final_session, stream=True):
            partial += token
            final_history[-1]["content"] = partial
            
            # Detect mode
            emoji = get_mode_emoji(mode)
            final_mode = f"{emoji} {mode.capitalize()} Mode"
            
            yield final_history, final_mode, final_session, final_memories, gr.update(), None
            
        # Refreshed dropdown at end
        previews = get_session_previews()
        choices = [(f"{p['preview'][:30]}... ({p['msg_count']} msgs)", p["session_id"]) for p in previews]
        final_dropdown = gr.update(choices=choices, value=final_session)
        
        # Audio reply generation
        audio_reply = None
        if voice_enabled and partial and not partial.startswith("⚠️ [Noor Error]"):
            try:
                audio_reply = speak_text(partial)
            except Exception as err:
                print(f"[Noor Voice] Failed to generate audio reply: {err}")
                
        yield final_history, final_mode, final_session, final_memories, final_dropdown, audio_reply
        
    except Exception as e:
        print(f"[Noor Voice] Error in process_voice_input chat: {e}")
        yield final_history, final_mode, final_session, final_memories, final_dropdown, None


def ingest_file(file_obj) -> str:
    """Ingest an uploaded file into the knowledge base."""
    if file_obj is None:
        return "No file selected."
    if not EMBEDDINGS_AVAILABLE:
        return "⚠️ Embedding model not available. Run: ollama pull nomic-embed-text"

    filepath = Path(file_obj.name)
    filename = filepath.name
    suffix = filepath.suffix.lower()

    try:
        text = ""
        if suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(filepath))
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
        elif suffix in (".txt", ".md", ".py", ".js", ".ts", ".json", ".csv"):
            text = filepath.read_text(encoding="utf-8", errors="replace")
        else:
            return f"⚠️ Unsupported file type: {suffix}"

        if not text.strip():
            return "⚠️ File appears to be empty."

        chunks = chunk_and_embed(text)
        ingest_chunks(filename=filename, chunks=chunks, filepath=str(filepath))
        return f"✅ Ingested **{filename}** — {len(chunks)} chunks, {len(text):,} characters."

    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Build UI
# ─────────────────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    init_db()
    ollama_ok = check_ollama()["status"] == "ok"
    
    # Check if OpenRouter or Gemini Cloud model is active
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY", ""))
    has_gemini = bool(os.getenv("GEMINI_API_KEY", ""))
    
    if has_openrouter:
        model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")
        short_name = model_name.split("/")[-1] if "/" in model_name else model_name
        status_text = f"Cloud Model: OpenRouter - {short_name} (Grounding Enabled)"
    elif has_gemini:
        status_text = "Cloud Model: Gemini 2.0 Flash (Grounding Enabled)"
    else:
        status_text = "Local Models: Auto-routed (Qwen 2.5 7B / Gemma 4)"

    with gr.Blocks(
        title="Noor -- Personal AI Companion",
    ) as demo:

        # ── Session state ──────────────────────────────────────────────────
        session_id = gr.State(value=str(uuid.uuid4()))

        # ── Header ────────────────────────────────────────────────────────
        gr.HTML("""
        <div class="noor-header">
            <div class="noor-logo">✨</div>
            <div>
                <div class="noor-title">Noor</div>
                <div class="noor-subtitle">Personal AI Companion — Phase 1</div>
            </div>
            <div class="mode-badge" id="mode-badge">😊 Friend Mode</div>
        </div>
        """)

        # Status warning if Ollama is down
        if not ollama_ok and not has_gemini and not has_openrouter:
            gr.HTML("""
            <div style="background:#7f1d1d;border:1px solid #ef4444;border-radius:10px;
                        padding:12px 16px;margin:12px;color:#fca5a5;font-size:14px;">
                ⚠️ <strong>Ollama is not running.</strong>
                Start it with: <code>ollama serve</code>
            </div>
            """)

        with gr.Row(equal_height=True):
            # ── Left Sidebar: Chat History ─────────────────────────────────
            with gr.Column(scale=3, min_width=200):
                gr.Markdown("### 💬 Chat History")
                history_dropdown = gr.Dropdown(
                    label="Select past conversation",
                    choices=[],
                    value=None,
                    interactive=True,
                    allow_custom_value=True,
                )
                new_chat_btn = gr.Button("➕ New Conversation", elem_classes=["primary-btn"])
                gr.Markdown("---")
                voice_toggle = gr.Checkbox(
                    label="🔊 Enable Voice Replies",
                    value=False,
                    interactive=True,
                )
                gr.Markdown("---")
                gr.HTML("""
                <div style="font-size:11px;color:var(--text-muted);padding:4px 0;">
                    Select a conversation from the list above to resume chatting.
                </div>
                """)

            # ── Main chat area ─────────────────────────────────────────────
            with gr.Column(scale=7):
                with gr.Tabs():
                    with gr.TabItem("💬 Chat"):
                        chatbot = gr.Chatbot(
                            label="",
                            height=520,
                            show_label=False,
                            elem_classes=["chatbot"],
                            avatar_images=(None, "https://api.dicebear.com/7.x/bottts/svg?seed=noor"),
                        )
                        mode_display = gr.Textbox(
                            value="😊 Friend Mode",
                            interactive=False,
                            show_label=False,
                            elem_id="mode-display",
                            container=False,
                        )
                        audio_output = gr.Audio(
                            visible=False,
                            autoplay=True,
                            type="filepath",
                            label="Noor Voice Output",
                        )
                        with gr.Row():
                            with gr.Column(scale=1):
                                with gr.Accordion("🎙️ Voice Input (Microphone)", open=False):
                                    voice_input = gr.Audio(
                                        sources=["microphone"],
                                        type="filepath",
                                        format="wav",
                                        show_label=False,
                                    )
                            with gr.Column(scale=1):
                                with gr.Accordion("🖼️ Image Input (Vision)", open=False):
                                    image_input = gr.Image(
                                        type="filepath",
                                        label="Upload image",
                                        show_label=False,
                                    )
                        with gr.Row(elem_classes=["input-row"]):
                            msg_input = gr.Textbox(
                                placeholder="Talk to Noor...",
                                show_label=False,
                                scale=9,
                                container=False,
                                lines=1,
                                max_lines=5,
                             )
                            send_btn = gr.Button("Send", scale=1, elem_classes=["primary-btn"])

                        with gr.Row():
                            screenshot_btn = gr.Button("📷 Take Screenshot", size="sm")
                            browser_btn = gr.Button("🖥️ Open Browser", size="sm")
                            notepad_btn = gr.Button("📝 Open Notepad", size="sm")
                            clipboard_btn = gr.Button("📋 Read Clipboard", size="sm")
                            active_window_btn = gr.Button("🔍 Active Window", size="sm")
                            clear_btn = gr.Button("🗑️ New Session", size="sm")
                        
                        gr.HTML(f'<div class="status-bar" style="margin-top: 10px;"><span><span class="status-dot"></span>{status_text}</span></div>')

                    with gr.TabItem("📄 Knowledge Base"):
                        gr.Markdown("### Upload Documents\nDrop files here to add them to Noor's knowledge base.")
                        file_upload = gr.File(
                            label="Upload PDF, TXT, MD, PY, JS, JSON, CSV",
                            file_types=[".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json", ".csv"],
                        )
                        ingest_btn = gr.Button("📥 Ingest Document", elem_classes=["primary-btn"])
                        ingest_status = gr.Markdown("")

                    with gr.TabItem("🕸️ Knowledge Graph"):
                        gr.Markdown("### 🕸️ Personal Knowledge Graph\nRelational graph summary extracted dynamically from your conversations.")
                        graph_display = gr.Textbox(
                            value=get_graph_summary(),
                            label="Extracted Entity Relationships",
                            interactive=False,
                            lines=20,
                            max_lines=30,
                        )
                        refresh_graph_btn = gr.Button("🔄 Refresh Graph", elem_classes=["primary-btn"])

                    with gr.TabItem("⚙️ Automation Tasks"):
                        gr.Markdown("### ⚙️ Background Automation Tasks\nSchedule background tasks, reminders, and regular checks.")
                        tasks_display = gr.Textbox(
                            value=get_tasks_summary_text(),
                            label="Active Automation Tasks",
                            interactive=False,
                            lines=12,
                            max_lines=15,
                        )
                        refresh_tasks_btn = gr.Button("🔄 Refresh Tasks", size="sm")
                        
                        gr.Markdown("---")
                        gr.Markdown("### ➕ Add New Task")
                        with gr.Row():
                            task_desc_input = gr.Textbox(
                                label="Task Description",
                                placeholder="e.g. Remind me to stand up and stretch",
                                scale=3
                            )
                            trigger_type = gr.Radio(
                                choices=["Interval (Seconds)", "Daily Time (HH:MM)"],
                                value="Interval (Seconds)",
                                label="Trigger Type",
                                scale=2
                            )
                            trigger_val = gr.Textbox(
                                label="Value",
                                placeholder="e.g. 60 or 14:30",
                                scale=2
                            )
                        add_task_btn = gr.Button("➕ Schedule Task", elem_classes=["primary-btn"])
                        add_task_status = gr.Markdown("")
                        
                        gr.Markdown("---")
                        gr.Markdown("### 🗑️ Delete Task")
                        with gr.Row():
                            delete_id_input = gr.Number(
                                label="Task ID to Delete",
                                precision=0,
                                scale=2
                            )
                            delete_task_btn = gr.Button("🗑️ Delete Task", variant="stop", scale=1)
                        delete_task_status = gr.Markdown("")

                    with gr.TabItem("✨ Proactive Intelligence"):
                        gr.Markdown("### ✨ Proactive Suggestions & Insights\nSuggestions generated by Noor's background daemon based on files, clipboards, and workspace focus.")
                        proactive_display = gr.Textbox(
                            value=get_proactive_suggestions_text(),
                            label="Unread Alerts & Insights",
                            interactive=False,
                            lines=15,
                            max_lines=25,
                        )
                        with gr.Row():
                            refresh_proactive_btn = gr.Button("🔄 Refresh Alerts", size="sm")
                            clear_proactive_btn = gr.Button("🗑️ Clear All Alerts", variant="stop", size="sm")
                        proactive_status = gr.Markdown("")

            # ── Memory & Logs sidebar ──────────────────────────────────────
            with gr.Column(scale=3):
                gr.Markdown("### 🧠 Noor's Memory")
                memory_display = gr.Textbox(
                    value=get_memories_text(),
                    label="",
                    interactive=False,
                    lines=10,
                    max_lines=12,
                    show_label=False,
                )
                refresh_mem_btn = gr.Button("🔄 Refresh Memory", size="sm")
                
                gr.Markdown("### 🤖 Agent System Logs")
                agent_logs_display = gr.Textbox(
                    value=get_agent_logs_text(),
                    label="",
                    interactive=False,
                    lines=10,
                    max_lines=12,
                    show_label=False,
                )
                refresh_logs_btn = gr.Button("🔄 Refresh Logs", size="sm")

        # ── Event handlers ─────────────────────────────────────────────────
        send_btn.click(
            fn=respond,
            inputs=[msg_input, chatbot, session_id, mode_display, voice_toggle, image_input],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        ).then(fn=lambda: ("", None), outputs=[msg_input, image_input])

        msg_input.submit(
            fn=respond,
            inputs=[msg_input, chatbot, session_id, mode_display, voice_toggle, image_input],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        ).then(fn=lambda: ("", None), outputs=[msg_input, image_input])

        voice_input.change(
            fn=process_voice_input,
            inputs=[voice_input, chatbot, session_id, mode_display, voice_toggle],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        ).then(fn=lambda: None, outputs=[voice_input])

        screenshot_btn.click(
            fn=take_screenshot_ui,
            inputs=[chatbot, session_id, mode_display, voice_toggle],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        )

        browser_btn.click(
            fn=open_browser_ui,
            inputs=[chatbot, session_id, mode_display, voice_toggle],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        )

        notepad_btn.click(
            fn=open_notepad_ui,
            inputs=[chatbot, session_id, mode_display, voice_toggle],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        )

        clipboard_btn.click(
            fn=read_clipboard_ui,
            inputs=[chatbot, session_id, mode_display, voice_toggle],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        )

        active_window_btn.click(
            fn=active_window_ui,
            inputs=[chatbot, session_id, mode_display, voice_toggle],
            outputs=[chatbot, mode_display, session_id, memory_display, history_dropdown, audio_output],
        )

        clear_btn.click(
            fn=clear_chat,
            inputs=[session_id],
            outputs=[chatbot, session_id, mode_display, memory_display, history_dropdown],
        )

        new_chat_btn.click(
            fn=start_new_chat,
            inputs=[],
            outputs=[chatbot, session_id, mode_display, memory_display, history_dropdown],
        )

        history_dropdown.change(
            fn=load_session,
            inputs=[history_dropdown],
            outputs=[chatbot, session_id, mode_display, memory_display],
        )

        ingest_btn.click(
            fn=ingest_file,
            inputs=[file_upload],
            outputs=[ingest_status],
        )

        refresh_mem_btn.click(
            fn=get_memories_text,
            outputs=[memory_display],
        )

        refresh_graph_btn.click(
            fn=get_graph_summary,
            outputs=[graph_display],
        )

        refresh_logs_btn.click(
            fn=get_agent_logs_text,
            outputs=[agent_logs_display],
        )

        refresh_tasks_btn.click(
            fn=get_tasks_summary_text,
            outputs=[tasks_display],
        )

        add_task_btn.click(
            fn=add_task_ui,
            inputs=[task_desc_input, trigger_type, trigger_val],
            outputs=[add_task_status, tasks_display],
        ).then(fn=lambda: ("", ""), outputs=[task_desc_input, trigger_val])

        delete_task_btn.click(
            fn=delete_task_ui,
            inputs=[delete_id_input],
            outputs=[delete_task_status, tasks_display],
        ).then(fn=lambda: None, outputs=[delete_id_input])

        refresh_proactive_btn.click(
            fn=get_proactive_suggestions_text,
            outputs=[proactive_display],
        )

        clear_proactive_btn.click(
            fn=clear_proactive_suggestions,
            outputs=[proactive_status, proactive_display],
        )

        # Page load triggers
        demo.load(
            fn=on_load_ui,
            inputs=[],
            outputs=[history_dropdown],
        )

    return demo


def launch():
    """Launch the Gradio UI."""
    try:
        from brain.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"[Noor] Failed to start background scheduler: {e}")

    try:
        from brain.proactive_daemon import start_proactive_daemon
        start_proactive_daemon()
    except Exception as e:
        print(f"[Noor] Failed to start proactive daemon: {e}")

    demo = build_ui()
    demo.launch(
        server_name=UI_HOST,
        server_port=UI_PORT,
        share=os.getenv("UI_SHARE", "false").lower() in ("true", "1", "yes"),
        show_error=True,
        favicon_path=None,
        theme=gr.themes.Base(
            primary_hue="violet",
            neutral_hue="slate",
        ),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    launch()

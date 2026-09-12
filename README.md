# Noor — Personal AI Companion
## Phase 1: Foundation Layer

```
✨ Local-first • No API keys • Always on
```

---

## Quick Start

```powershell
# 1. Make sure Ollama is running
ollama serve

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch Noor
python main.py
```

Then open: **http://localhost:7860**

---

## What's Inside

```
Noor/
├── main.py              ← Start everything here
├── .env                 ← Configuration
├── requirements.txt
│
├── brain/
│   ├── llm.py           ← Ollama wrapper + chat pipeline
│   ├── memory.py        ← SQLite + ChromaDB memory
│   ├── personality.py   ← Mode detection + system prompt
│   └── embeddings.py    ← Local text embeddings
│
├── api/
│   └── server.py        ← FastAPI REST backend (:8000)
│
├── ui/
│   └── chat_ui.py       ← Gradio dark chat UI (:7860)
│
├── knowledge/           ← Drop files here to teach Noor
├── data/noor.db         ← SQLite database (auto-created)
├── chroma_db/           ← Vector store (auto-created)
└── configs/
    └── personality.txt  ← Edit Noor's personality
```

---

## Models Used

| Purpose | Model |
|---------|-------|
| Brain (conversation) | `gemma4:latest` |
| Coding tasks | `qwen2.5-coder:latest` |
| Embeddings | `nomic-embed-text:latest` |

---

## API Endpoints

```
GET  /status             → Health check
POST /chat               → Send a message (streaming)
GET  /memories           → List all memories
POST /memories           → Add a memory manually
GET  /search?q=...       → Semantic search
POST /ingest             → Upload a document
GET  /sessions           → List sessions
```

Swagger UI: **http://localhost:8000/docs**

---

## Dynamic Modes

Noor automatically switches between:

| Mode | Trigger |
|------|---------|
| 😊 Friend | Default — casual chat |
| 🎯 Mentor | Goals, career, decisions |
| 🔬 Researcher | Papers, concepts, analysis |
| 💻 Coder | Code, debugging, tech |

---

## Roadmap

- [x] Phase 1 — Foundation (Chat, Memory, Personality, UI, API)
- [ ] Phase 2 — Agent System (LangGraph, Tools, Internet)
- [ ] Phase 3 — Voice (Whisper + Piper + Wake Word)
- [ ] Phase 4 — Computer Control (PyAutoGUI, Playwright)
- [ ] Phase 5 — Vision (OpenCV, EasyOCR)
- [ ] Phase 6 — Multi-Model Routing
- [ ] Phase 7 — Knowledge Vault + RAG

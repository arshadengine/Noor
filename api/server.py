"""
api/server.py
─────────────────────────────────────────────────────
Noor's FastAPI REST Backend.

Endpoints:
  POST /chat          → Send a message, get response (streaming or not)
  GET  /memories      → List all stored memories
  POST /memories      → Add a manual memory
  DELETE /memories/{id} → Delete a memory
  GET  /search        → Semantic search across memory
  GET  /sessions      → List all conversation sessions
  GET  /status        → Health check + model info
  POST /ingest        → Ingest a document into the knowledge base
"""

from __future__ import annotations

import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from brain.llm import chat, check_ollama, simple_query
from brain.memory import (
    get_all_memories, save_memory, get_all_sessions,
    get_recent_messages, semantic_search_memories,
    ingest_chunks, init_db
)

try:
    from brain.embeddings import embed, chunk_and_embed
    EMBEDDINGS_AVAILABLE = True
except Exception:
    EMBEDDINGS_AVAILABLE = False

KNOWLEDGE_PATH = Path(os.getenv("KNOWLEDGE_PATH", "D:/Noor/knowledge"))

app = FastAPI(
    title="Noor API",
    description="Local-first personal AI companion REST interface",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    mode: str
    session_id: str


class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1)
    importance: int = Field(default=2, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/status")
async def status():
    """Health check endpoint."""
    ollama_status = check_ollama()
    return {
        "noor": "running",
        "ollama": ollama_status,
        "embeddings": EMBEDDINGS_AVAILABLE,
    }


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Send a message to Noor.
    - If stream=True, returns a streaming text/event-stream response.
    - If stream=False, returns a JSON ChatResponse.
    """
    session_id = req.session_id or str(uuid.uuid4())

    if req.stream:
        def _generate():
            final_mode = "friend"
            for token, mode in chat(req.message, session_id, stream=True):
                final_mode = mode
                yield token
            # Send mode as a final SSE comment
            yield f"\n\n[mode:{final_mode}][session:{session_id}]"

        return StreamingResponse(_generate(), media_type="text/plain")

    else:
        full_response = ""
        final_mode = "friend"
        for token, mode in chat(req.message, session_id, stream=False):
            full_response += token
            final_mode = mode

        return ChatResponse(
            response=full_response,
            mode=final_mode,
            session_id=session_id,
        )


@app.get("/sessions")
async def list_sessions():
    """List all conversation sessions."""
    return get_all_sessions()


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 50):
    """Get messages from a specific session."""
    return get_recent_messages(session_id, limit=limit)


@app.get("/memories")
async def list_memories(limit: int = Query(default=50, le=500)):
    """List all stored memories."""
    return get_all_memories(limit=limit)


@app.post("/memories", status_code=201)
async def create_memory(mem: MemoryCreate):
    """Manually add a memory."""
    embedding = None
    if EMBEDDINGS_AVAILABLE:
        try:
            embedding = embed(mem.content)
        except Exception:
            pass
    mem_id = save_memory(mem.content, importance=mem.importance, tags=mem.tags, embedding=embedding)
    return {"id": mem_id, "content": mem.content}


@app.get("/search")
async def search(q: str = Query(..., min_length=1), top_k: int = Query(default=5, le=20)):
    """Semantic search across stored memories."""
    if not EMBEDDINGS_AVAILABLE:
        raise HTTPException(503, "Embedding model not available. Pull nomic-embed-text via Ollama.")

    query_vec = embed(q)
    results = semantic_search_memories(query_vec, top_k=top_k)
    return {"query": q, "results": results}


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingest a document into Noor's knowledge base."""
    if not EMBEDDINGS_AVAILABLE:
        raise HTTPException(503, "Embedding model not available.")

    KNOWLEDGE_PATH.mkdir(parents=True, exist_ok=True)
    filename = file.filename or "unknown"
    save_path = KNOWLEDGE_PATH / filename

    content_bytes = await file.read()

    # Extract text based on file type
    text = ""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as e:
            raise HTTPException(400, f"Failed to parse PDF: {e}")
    elif suffix in (".txt", ".md", ".py", ".js", ".ts", ".json", ".csv"):
        text = content_bytes.decode("utf-8", errors="replace")
    else:
        raise HTTPException(400, f"Unsupported file type: {suffix}. Supported: pdf, txt, md, py, js, ts, json, csv")

    if not text.strip():
        raise HTTPException(400, "Document appears to be empty.")

    # Save file to disk
    save_path.write_bytes(content_bytes)

    # Chunk and embed
    chunks = chunk_and_embed(text)
    ingest_chunks(filename=filename, chunks=chunks, filepath=str(save_path))

    return {
        "filename": filename,
        "chunks": len(chunks),
        "characters": len(text),
        "status": "ingested"
    }

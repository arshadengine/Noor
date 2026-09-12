"""
brain/memory.py
─────────────────────────────────────────────────────
Noor's Two-Layer Memory System.

Layer 1 — SQLite:  Structured data (conversations, explicit memories, preferences)
Layer 2 — ChromaDB: Semantic vector search over all conversation history

The two layers are kept in sync automatically.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path(os.getenv("DB_PATH", "D:/Noor/data/noor.db"))
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "D:/Noor/chroma_db"))
TOP_K = int(os.getenv("TOP_K_MEMORIES", "5"))

# ──────────────────────────────────────────────────────────────────────────────
# SQLite Layer
# ──────────────────────────────────────────────────────────────────────────────

from brain.db import get_db as _get_db, init_db_schema as init_db


# ──────────────────────────────────────────────────────────────────────────────
# ChromaDB Layer
# ──────────────────────────────────────────────────────────────────────────────

def _get_chroma():
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client


def _get_collection(name: str):
    client = _get_chroma()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )


# ──────────────────────────────────────────────────────────────────────────────
# Conversation Management
# ──────────────────────────────────────────────────────────────────────────────

def save_message(
    session_id: str,
    role: str,
    content: str,
    mode: str = "friend",
    embedding: list[float] | None = None,
) -> str:
    """Save a conversation message to SQLite and optionally index it in ChromaDB."""
    msg_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with _get_db() as conn:
        conn.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, session_id, role, content, mode, now)
        )

    # Index in ChromaDB for semantic search
    if embedding is not None:
        col = _get_collection("conversations")
        col.add(
            ids=[msg_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"role": role, "session_id": session_id, "timestamp": now}]
        )

    return msg_id


def get_recent_messages(session_id: str, limit: int = 20) -> list[dict]:
    """Retrieve the most recent N messages for a session."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations "
            "WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_all_sessions() -> list[dict]:
    """Get a summary of all conversation sessions."""
    with _get_db() as conn:
        rows = conn.execute(
            """SELECT session_id, 
               COUNT(*) as msg_count,
               MIN(timestamp) as started,
               MAX(timestamp) as last_active
               FROM conversations GROUP BY session_id ORDER BY last_active DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Memory Management
# ──────────────────────────────────────────────────────────────────────────────

def save_memory(
    content: str,
    importance: int = 2,
    tags: list[str] | None = None,
    embedding: list[float] | None = None,
    source: str = "conversation",
    confidence: float = 1.0,
    metadata: dict | None = None,
) -> str:
    """Save an important fact or memory."""
    mem_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    tags_json = json.dumps(tags or [])
    metadata_json = json.dumps(metadata or {})

    with _get_db() as conn:
        conn.execute(
            "INSERT INTO memories (id, content, importance, tags, created_at, updated_at, source, confidence, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (mem_id, content, importance, tags_json, now, now, source, confidence, metadata_json)
        )

    if embedding is not None:
        col = _get_collection("memories")
        col.add(
            ids=[mem_id],
            embeddings=[embedding],
            documents=[content],
            metadatas={"importance": importance, "tags": tags_json, "source": source, "confidence": confidence}
        )

    return mem_id


def get_all_memories(limit: int = 50) -> list[dict]:
    """Retrieve all stored memories, ordered by importance then recency."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT id, content, importance, tags, created_at, source, confidence, metadata FROM memories "
            "ORDER BY importance DESC, created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [
        {
            "id": r["id"],
            "content": r["content"],
            "importance": r["importance"],
            "tags": json.loads(r["tags"]),
            "created_at": r["created_at"],
            "source": r["source"] if "source" in r.keys() else "conversation",
            "confidence": r["confidence"] if "confidence" in r.keys() else 1.0,
            "metadata": json.loads(r["metadata"]) if ("metadata" in r.keys() and r["metadata"]) else {},
        }
        for r in rows
    ]


def semantic_search_memories(query_embedding: list[float], top_k: int = TOP_K) -> list[str]:
    """Find the most semantically relevant memories for a query."""
    try:
        col = _get_collection("memories")
        if col.count() == 0:
            return []
        results = col.query(query_embeddings=[query_embedding], n_results=min(top_k, col.count()))
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


def semantic_search_conversations(query_embedding: list[float], top_k: int = TOP_K) -> list[str]:
    """Find the most semantically relevant past conversation turns."""
    try:
        col = _get_collection("conversations")
        if col.count() == 0:
            return []
        results = col.query(query_embeddings=[query_embedding], n_results=min(top_k, col.count()))
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


def search_knowledge(query_embedding: list[float], top_k: int = TOP_K) -> list[str]:
    """Search the ingested knowledge base."""
    try:
        col = _get_collection("knowledge")
        if col.count() == 0:
            return []
        results = col.query(query_embeddings=[query_embedding], n_results=min(top_k, col.count()))
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


def retrieve_context(query_embedding: list[float]) -> list[str]:
    """
    Master retrieval function: combines memories + past conversations + knowledge.
    Returns a deduplicated list of relevant context strings.
    """
    memories = semantic_search_memories(query_embedding, top_k=3)
    convs = semantic_search_conversations(query_embedding, top_k=3)
    knowledge = search_knowledge(query_embedding, top_k=2)

    # Deduplicate while preserving order
    seen: set[str] = set()
    context: list[str] = []
    for item in memories + convs + knowledge:
        if item not in seen:
            seen.add(item)
            context.append(item)

    return context


# ──────────────────────────────────────────────────────────────────────────────
# Preferences
# ──────────────────────────────────────────────────────────────────────────────

def set_preference(key: str, value: str) -> None:
    now = datetime.utcnow().isoformat()
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO preferences(key, value, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now)
        )


def get_preference(key: str, default: str = "") -> str:
    with _get_db() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge Base Ingestion
# ──────────────────────────────────────────────────────────────────────────────

def ingest_chunks(
    filename: str,
    chunks: list[tuple[str, list[float]]],
    filepath: str = "",
) -> None:
    """Store document chunks in ChromaDB and log the ingestion in SQLite."""
    doc_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with _get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_docs VALUES (?, ?, ?, ?, ?)",
            (doc_id, filename, filepath, now, len(chunks))
        )

    col = _get_collection("knowledge")
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    texts = [c[0] for c in chunks]
    vecs = [c[1] for c in chunks]
    metas = [{"filename": filename, "chunk": i} for i in range(len(chunks))]

    col.add(ids=ids, embeddings=vecs, documents=texts, metadatas=metas)


def extract_facts_from_message(content: str) -> list[tuple[str, int, list[str]]]:
    """
    Simple rule-based fact extractor.
    Returns list of (fact_text, importance, tags).
    
    In Phase 2 this will be replaced with LLM-based extraction.
    """
    facts = []
    text = content.lower()

    patterns = [
        (r"my name is (\w+)", "name", 5, ["identity"]),
        (r"i(?:'m| am) (\w+)", "identity", 3, ["identity"]),
        (r"i (?:work|worked) (?:at|for|in) ([a-z0-9 ]+)", "work", 4, ["career"]),
        (r"i(?:'m| am) (?:studying|learning) ([a-z0-9 ]+)", "study", 3, ["education"]),
        (r"i (?:like|love|enjoy) ([a-z0-9 ,]+)", "preference", 2, ["personality"]),
        (r"i (?:hate|dislike|don't like) ([a-z0-9 ,]+)", "preference", 2, ["personality"]),
        (r"i(?:'m| am) (?:building|working on|making) ([a-z0-9 ]+)", "project", 4, ["projects"]),
    ]

    for pattern, fact_type, importance, tags in patterns:
        match = re.search(pattern, text)
        if match:
            fact = f"Arshad {fact_type}: {match.group(1).strip()}"
            facts.append((fact, importance, tags + [fact_type]))

    return facts


def get_session_previews() -> list[dict]:
    """Retrieve all sessions with their first user message as preview, sorted by last active time."""
    with _get_db() as conn:
        rows = conn.execute("""
            SELECT c.session_id, 
                   (SELECT content FROM conversations WHERE session_id = c.session_id AND role = 'user' ORDER BY timestamp ASC LIMIT 1) as first_msg,
                   MAX(c.timestamp) as last_active,
                   COUNT(*) as msg_count
            FROM conversations c
            GROUP BY c.session_id
            ORDER BY last_active DESC
        """).fetchall()
    return [
        {
            "session_id": r["session_id"],
            "preview": r["first_msg"] or "Empty Chat",
            "last_active": r["last_active"],
            "msg_count": r["msg_count"]
        }
        for r in rows
    ]


def get_session_history_for_ui(session_id: str) -> list[dict]:
    """Retrieve all messages for a session in chronological order."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, mode FROM conversations WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"], "mode": r["mode"]} for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Learning Engine Helpers
# ──────────────────────────────────────────────────────────────────────────────

def save_correction(pattern: str, correction: str) -> None:
    """Save a user correction rule to the database."""
    now = datetime.utcnow().isoformat()
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO corrections(pattern, correction, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(pattern) DO UPDATE SET correction=excluded.correction",
            (pattern.lower().strip(), correction.strip(), now)
        )


def find_matching_corrections(text: str) -> list[str]:
    """Find any correction rules whose patterns match the input text."""
    text_lower = text.lower()
    matches = []
    try:
        with _get_db() as conn:
            rows = conn.execute("SELECT pattern, correction FROM corrections").fetchall()
        for r in rows:
            if r["pattern"] in text_lower:
                matches.append(r["correction"])
    except Exception as e:
        print(f"[Noor Memory] Error finding corrections: {e}")
    return matches


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge Graph Helpers
# ──────────────────────────────────────────────────────────────────────────────

def add_graph_node(node_id: str, name: str, node_type: str) -> None:
    """Add a node to the Knowledge Graph."""
    node_id_clean = node_id.lower().strip().replace(" ", "_")
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO graph_nodes(id, name, type) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, type=excluded.type",
            (node_id_clean, name.strip(), node_type.strip())
        )


def add_graph_edge(source_id: str, target_id: str, relation: str) -> None:
    """Add a directed edge to the Knowledge Graph, creating nodes if they don't exist."""
    src_clean = source_id.lower().strip().replace(" ", "_")
    tgt_clean = target_id.lower().strip().replace(" ", "_")
    rel_clean = relation.lower().strip().replace(" ", "_")
    
    # Auto-create nodes of type 'concept' if they don't exist yet
    with _get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO graph_nodes(id, name, type) VALUES (?, ?, 'concept')",
            (src_clean, source_id)
        )
        conn.execute(
            "INSERT OR IGNORE INTO graph_nodes(id, name, type) VALUES (?, ?, 'concept')",
            (tgt_clean, target_id)
        )
        conn.execute(
            "INSERT OR IGNORE INTO graph_edges(source_id, target_id, relation) VALUES (?, ?, ?)",
            (src_clean, tgt_clean, rel_clean)
        )


def get_graph_data() -> dict:
    """Retrieve all nodes and edges in the Knowledge Graph."""
    with _get_db() as conn:
        nodes = conn.execute("SELECT id, name, type FROM graph_nodes").fetchall()
        edges = conn.execute("SELECT source_id, target_id, relation FROM graph_edges").fetchall()
    return {
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges]
    }


def get_graph_summary() -> str:
    """Get a readable textual summary of all graph relationships."""
    with _get_db() as conn:
        rows = conn.execute("""
            SELECT n1.name as src, e.relation as rel, n2.name as tgt
            FROM graph_edges e
            JOIN graph_nodes n1 ON e.source_id = n1.id
            JOIN graph_nodes n2 ON e.target_id = n2.id
        """).fetchall()
    
    if not rows:
        return "Knowledge Graph is empty. Share relationships (e.g. 'Arshad works on Noor') to populate it!"
        
    lines = []
    for r in rows:
        lines.append(f"• {r['src']} ──[{r['rel']}]──> {r['tgt']}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Agent Logging Helpers
# ──────────────────────────────────────────────────────────────────────────────

def log_agent_action(agent_name: str, action: str, result: str = "") -> None:
    """Log an agent action to the database."""
    now = datetime.utcnow().isoformat()
    try:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO agent_logs(agent_name, action, result, timestamp) VALUES (?, ?, ?, ?)",
                (agent_name, action, result, now)
            )
    except Exception as e:
        print(f"[Noor Memory] Failed to log agent action: {e}")


def get_recent_agent_logs(limit: int = 15) -> list[dict]:
    """Retrieve the most recent agent execution logs."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT agent_name, action, result, timestamp FROM agent_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Automation Scheduler Helpers
# ──────────────────────────────────────────────────────────────────────────────

def add_automation_task(task_description: str, trigger_time: str = None, interval_seconds: int = None) -> int:
    """Register a new scheduled automation task."""
    with _get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO automation_tasks (task_description, trigger_time, interval_seconds, status) "
            "VALUES (?, ?, ?, 'active')",
            (task_description, trigger_time, interval_seconds)
        )
        return cursor.lastrowid or 0


def get_automation_tasks() -> list[dict]:
    """Retrieve all scheduled tasks."""
    try:
        with _get_db() as conn:
            rows = conn.execute("SELECT id, task_description, trigger_time, interval_seconds, last_run, status FROM automation_tasks").fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def update_automation_task_last_run(task_id: int) -> None:
    """Update the last run timestamp of a task."""
    now = datetime.utcnow().isoformat()
    with _get_db() as conn:
        conn.execute(
            "UPDATE automation_tasks SET last_run = ? WHERE id = ?",
            (now, task_id)
        )


def delete_automation_task(task_id: int) -> None:
    """Delete a scheduled task."""
    with _get_db() as conn:
        conn.execute("DELETE FROM automation_tasks WHERE id = ?", (task_id,))


# ──────────────────────────────────────────────────────────────────────────────
# Proactive Suggestions Helpers
# ──────────────────────────────────────────────────────────────────────────────

def save_proactive_suggestion(title: str, content: str, event_type: str, action_data: dict | None = None) -> str:
    """Save a proactive suggestion/insight to SQLite."""
    suggestion_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    action_data_json = json.dumps(action_data or {})

    with _get_db() as conn:
        conn.execute(
            "INSERT INTO proactive_suggestions (id, title, content, event_type, status, action_data, created_at) "
            "VALUES (?, ?, ?, ?, 'unread', ?, ?)",
            (suggestion_id, title, content, event_type, action_data_json, now)
        )
    return suggestion_id


def get_unread_proactive_suggestions(limit: int = 20) -> list[dict]:
    """Retrieve all unread proactive suggestions."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT id, title, content, event_type, status, action_data, created_at "
                "FROM proactive_suggestions WHERE status = 'unread' "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "event_type": r["event_type"],
                "status": r["status"],
                "action_data": json.loads(r["action_data"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[Noor Memory] Failed to get proactive suggestions: {e}")
        return []


def mark_proactive_suggestion_status(suggestion_id: str, status: str) -> None:
    """Mark a proactive suggestion's status (read, accepted, dismissed)."""
    with _get_db() as conn:
        conn.execute(
            "UPDATE proactive_suggestions SET status = ? WHERE id = ?",
            (status, suggestion_id)
        )



"""
brain/embeddings.py
─────────────────────────────────────────────────────
Local embedding engine using Ollama's nomic-embed-text model.

No OpenAI key required. Everything runs on your machine.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Generator

import ollama
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

EMBED_MODEL = os.getenv("NOOR_EMBED_MODEL", "nomic-embed-text:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Chunk settings for long documents
CHUNK_SIZE = 512       # characters per chunk
CHUNK_OVERLAP = 64     # overlap between chunks


def _ensure_model() -> None:
    """Pull the embedding model if not already available."""
    try:
        available = {m.model for m in ollama.list().models}
        if EMBED_MODEL not in available:
            print(f"[Noor] Pulling embedding model: {EMBED_MODEL} ...")
            ollama.pull(EMBED_MODEL)
            print(f"[Noor] {EMBED_MODEL} ready.")
    except Exception as e:
        print(f"[Noor] Warning: Could not verify embedding model: {e}")


def embed(text: str) -> list[float]:
    """
    Generate an embedding vector for a given text string.
    Returns a list of floats (the embedding vector).
    """
    _ensure_model()
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of vectors."""
    return [embed(t) for t in texts]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Args:
        text: The full text to chunk
        chunk_size: Max characters per chunk
        overlap: How many characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at a sentence boundary
        if end < len(text):
            last_period = chunk.rfind(". ")
            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    
    return [c for c in chunks if c]


def chunk_and_embed(text: str) -> list[tuple[str, list[float]]]:
    """
    Chunk a document and embed each chunk.
    Returns list of (chunk_text, embedding_vector) tuples.
    """
    chunks = chunk_text(text)
    results = []
    for chunk in chunks:
        vec = embed(chunk)
        results.append((chunk, vec))
    return results

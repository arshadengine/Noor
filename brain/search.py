"""
brain/search.py
─────────────────────────────────────────────────────
Web search utilities for Noor using DuckDuckGo.
Allows Noor to fetch up-to-date live data.
"""

from __future__ import annotations
import re
import threading
from duckduckgo_search import DDGS

SEARCH_KEYWORDS = [
    r"\blatest\b", r"\bnews\b", r"\btoday's\b", r"\btodays?\b", r"\bcurrent\b", 
    r"\brecent\b", r"\bwho is\b", r"\bscore\b", r"\bweather\b", 
    r"\bupdate\b", r"\bwhat happened\b", r"\breleased?\b", r"\blaunch\b"
]


def needs_search(message: str) -> bool:
    """Detect if a user query requires real-time information."""
    msg = message.lower()
    return any(re.search(pattern, msg) for pattern in SEARCH_KEYWORDS)


def _web_search_raw(query: str, max_results: int = 3) -> list[str]:
    """Search DuckDuckGo for a query and return snippets."""
    try:
        print(f"[Noor] Searching web for: '{query}'...")
        with DDGS(timeout=8) as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            formatted = []
            for r in results:
                title = r.get("title", "No Title")
                body = r.get("body", "No Snippet")
                link = r.get("href", "")
                formatted.append(f"Title: {title}\nSnippet: {body}\nLink: {link}")
            return formatted
    except Exception as e:
        print(f"[Noor] Search failed: {e}")
        return []


def web_search(query: str, max_results: int = 3, timeout: float = 8.0) -> list[str]:
    """Execute web search inside a background thread with a strict timeout limit."""
    search_results = []
    
    def worker():
        try:
            res = _web_search_raw(query, max_results)
            search_results.extend(res)
        except Exception as e:
            print(f"[Noor] Threaded search worker exception: {e}")
            
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        print(f"[Noor] Web search timed out after {timeout}s. Returning empty context.")
        
    return search_results

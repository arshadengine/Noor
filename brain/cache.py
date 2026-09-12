"""
brain/cache.py
─────────────────────────────────────────────────────
Routing Decision & Short-Term Cache for Noor.

Caches model selection choices per task category to prevent redundant
scoring overhead for similar rapid tasks within a TTL window.
"""

from __future__ import annotations
import time
import hashlib
from typing import Any

CACHE_TTL_SECONDS = 300  # 5 minutes


class RoutingCache:
    _instance: RoutingCache | None = None

    def __new__(cls) -> RoutingCache:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = {}
        return cls._instance

    def _make_key(self, task_category: str, user_preference: str, constraints_hash: str) -> str:
        raw = f"{task_category}:{user_preference}:{constraints_hash}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, task_category: str, user_preference: str = "speed", constraints: dict[str, Any] | None = None) -> str | None:
        c_hash = str(sorted((constraints or {}).items()))
        key = self._make_key(task_category, user_preference, c_hash)
        entry = self._store.get(key)
        if not entry:
            return None
        
        timestamp, selected_model = entry
        if time.time() - timestamp > CACHE_TTL_SECONDS:
            del self._store[key]
            return None
        return selected_model

    def set(self, task_category: str, selected_model: str, user_preference: str = "speed", constraints: dict[str, Any] | None = None) -> None:
        c_hash = str(sorted((constraints or {}).items()))
        key = self._make_key(task_category, user_preference, c_hash)
        self._store[key] = (time.time(), selected_model)

    def clear(self) -> None:
        self._store.clear()


routing_cache = RoutingCache()

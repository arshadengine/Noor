"""
brain/providers/base.py
─────────────────────────────────────────────────────
Abstract Base Class for all LLM Providers in Noor.
Defines standard execution interface for streaming, non-streaming,
and health checks.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generator, Any


class BaseProvider(ABC):
    def __init__(self, name: str, default_model: str):
        self.name = name
        self.default_model = default_model

    @abstractmethod
    def generate(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> str:
        """Non-streaming text generation."""
        pass

    @abstractmethod
    def stream(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> Generator[str, None, None]:
        """Streaming token generator."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Verify API key, connectivity, and model availability."""
        pass

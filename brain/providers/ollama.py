"""
brain/providers/ollama.py
─────────────────────────────────────────────────────
Local Ollama Provider implementation for Noor.
"""

from __future__ import annotations
import os
import ollama
from typing import Generator, Any
from brain.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self, default_model: str | None = None):
        model = default_model or os.getenv("NOOR_HEAVY_MODEL", "gemma4:latest")
        super().__init__(name="ollama", default_model=model)

    def health_check(self) -> dict[str, Any]:
        try:
            models = ollama.list()
            model_names = [m.model for m in models.models]
            return {"status": "online", "models": model_names}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def generate(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> str:
        target_model = model or self.default_model
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            payload_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        response = ollama.chat(
            model=target_model,
            messages=payload_messages,
            stream=False,
            options={"temperature": 0.7, "repeat_penalty": 1.2}
        )
        return response["message"]["content"]

    def stream(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> Generator[str, None, None]:
        target_model = model or self.default_model
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            payload_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        stream_iter = ollama.chat(
            model=target_model,
            messages=payload_messages,
            stream=True,
            options={"temperature": 0.7, "repeat_penalty": 1.2}
        )
        for chunk in stream_iter:
            token = chunk["message"]["content"]
            if token:
                yield token

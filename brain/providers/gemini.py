"""
brain/providers/gemini.py
─────────────────────────────────────────────────────
Google Gemini Cloud Model Provider implementation for Noor.
"""

from __future__ import annotations
import os
from typing import Generator, Any
from brain.providers.base import BaseProvider

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiProvider(BaseProvider):
    def __init__(self, default_model: str | None = None):
        model = default_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        super().__init__(name="gemini", default_model=model)

    def _get_client(self):
        if not GEMINI_AVAILABLE:
            raise RuntimeError("google-genai package is not installed.")
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
        return genai.Client(api_key=api_key)

    def health_check(self) -> dict[str, Any]:
        if not GEMINI_AVAILABLE:
            return {"status": "error", "reason": "google-genai library missing"}
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return {"status": "error", "reason": "GEMINI_API_KEY missing"}
        return {"status": "online", "model": self.default_model}

    def _format_contents(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })
        return contents

    def generate(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> str:
        client = self._get_client()
        target_model = model or self.default_model
        contents = self._format_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=0.7,
        )
        response = client.models.generate_content(
            model=target_model,
            contents=contents,
            config=config
        )
        return response.text or ""

    def stream(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> Generator[str, None, None]:
        client = self._get_client()
        target_model = model or self.default_model
        contents = self._format_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=0.7,
        )
        response_stream = client.models.generate_content_stream(
            model=target_model,
            contents=contents,
            config=config
        )
        for chunk in response_stream:
            token = chunk.text
            if token:
                yield token

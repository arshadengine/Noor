"""
brain/providers/openrouter.py
─────────────────────────────────────────────────────
OpenRouter Cloud Model Provider implementation for Noor.
"""

from __future__ import annotations
import os
import json
import httpx
from typing import Generator, Any
from brain.providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    def __init__(self, default_model: str | None = None):
        model = default_model or os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")
        super().__init__(name="openrouter", default_model=model)

    def health_check(self) -> dict[str, Any]:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            return {"status": "error", "reason": "OPENROUTER_API_KEY missing"}
        return {"status": "online", "model": self.default_model}

    def _prepare_payload(self, messages: list[dict[str, Any]], model: str | None, system_prompt: str, stream: bool) -> tuple[dict[str, str], dict[str, Any]]:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is missing.")

        target_model = model or self.default_model
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Noor-AI",
            "X-Title": "Noor Companion",
        }

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            payload_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        payload = {
            "model": target_model,
            "messages": payload_messages,
            "stream": stream,
        }
        return headers, payload

    def generate(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> str:
        headers, payload = self._prepare_payload(messages, model, system_prompt, stream=False)
        url = "https://openrouter.ai/api/v1/chat/completions"
        timeout = httpx.Timeout(timeout=6.0, connect=3.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def stream(self, messages: list[dict[str, Any]], model: str | None = None, system_prompt: str = "") -> Generator[str, None, None]:
        headers, payload = self._prepare_payload(messages, model, system_prompt, stream=True)
        url = "https://openrouter.ai/api/v1/chat/completions"
        timeout = httpx.Timeout(timeout=6.0, connect=3.0)
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded = line.strip()
                        if decoded.startswith("data: "):
                            data_str = decoded[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data_json = json.loads(data_str)
                                token = data_json["choices"][0]["delta"].get("content", "")
                                if token:
                                    yield token
                            except Exception:
                                pass

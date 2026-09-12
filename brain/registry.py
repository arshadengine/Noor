"""
brain/registry.py
─────────────────────────────────────────────────────
Model Capability Registry & Constraint Definitions for Noor.

Stores static capability benchmark ratings (0-10) and hardware/API
constraints for candidate models across all integrated providers.
"""

from __future__ import annotations
from typing import Any

MODELS: dict[str, dict[str, Any]] = {
    "gemini_flash": {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "capabilities": {
            "chat": 9,
            "coding": 8,
            "debugging": 8,
            "reasoning": 10,
            "math": 10,
            "vision": 10,
            "ocr": 10,
            "planning": 10,
            "research": 10,
            "translation": 9,
        },
        "constraints": {
            "vision": True,
            "streaming": True,
            "max_context": 1000000,
            "supports_tools": True,
            "supports_json": True,
            "offline": False,
            "multimodal": True,
        },
        "speed_rating": 9,  # 1-10
    },
    "groq_llama70b": {
        "provider": "groq",
        "model_name": "llama-3.3-70b-versatile",
        "capabilities": {
            "chat": 9,
            "coding": 10,
            "debugging": 9,
            "reasoning": 8,
            "math": 8,
            "vision": 0,
            "ocr": 0,
            "planning": 8,
            "research": 8,
            "translation": 9,
        },
        "constraints": {
            "vision": False,
            "streaming": True,
            "max_context": 128000,
            "supports_tools": True,
            "supports_json": True,
            "offline": False,
            "multimodal": False,
        },
        "speed_rating": 10,  # Groq LPU fast inference
    },
    "openrouter_gemini": {
        "provider": "openrouter",
        "model_name": "google/gemini-2.0-flash",
        "capabilities": {
            "chat": 9,
            "coding": 8,
            "debugging": 8,
            "reasoning": 9,
            "math": 9,
            "vision": 9,
            "ocr": 9,
            "planning": 9,
            "research": 9,
            "translation": 9,
        },
        "constraints": {
            "vision": True,
            "streaming": True,
            "max_context": 1000000,
            "supports_tools": True,
            "supports_json": True,
            "offline": False,
            "multimodal": True,
        },
        "speed_rating": 8,
    },
    "ollama_qwen": {
        "provider": "ollama",
        "model_name": "qwen2.5-coder:latest",
        "capabilities": {
            "chat": 7,
            "coding": 9,
            "debugging": 8,
            "reasoning": 7,
            "math": 7,
            "vision": 0,
            "ocr": 0,
            "planning": 7,
            "research": 6,
            "translation": 7,
        },
        "constraints": {
            "vision": False,
            "streaming": True,
            "max_context": 32000,
            "supports_tools": False,
            "supports_json": True,
            "offline": True,
            "multimodal": False,
        },
        "speed_rating": 5,
    },
    "ollama_gemma": {
        "provider": "ollama",
        "model_name": "gemma4:latest",
        "capabilities": {
            "chat": 8,
            "coding": 7,
            "debugging": 7,
            "reasoning": 7,
            "math": 7,
            "vision": 0,
            "ocr": 0,
            "planning": 7,
            "research": 6,
            "translation": 8,
        },
        "constraints": {
            "vision": False,
            "streaming": True,
            "max_context": 8000,
            "supports_tools": False,
            "supports_json": False,
            "offline": True,
            "multimodal": False,
        },
        "speed_rating": 5,
    },
    "ollama_llama": {
        "provider": "ollama",
        "model_name": "llama3.2:latest",
        "capabilities": {
            "chat": 8,
            "coding": 7,
            "debugging": 7,
            "reasoning": 8,
            "math": 7,
            "vision": 0,
            "ocr": 0,
            "planning": 7,
            "research": 7,
            "translation": 8,
        },
        "constraints": {
            "vision": False,
            "streaming": True,
            "max_context": 128000,
            "supports_tools": False,
            "supports_json": True,
            "offline": True,
            "multimodal": False,
        },
        "speed_rating": 8,
    },
}

TASK_CAPABILITY_MAP: dict[str, str] = {
    "CHAT": "chat",
    "CODING": "coding",
    "DEBUGGING": "debugging",
    "REASONING": "reasoning",
    "MATH": "math",
    "VISION": "vision",
    "PLANNING": "planning",
    "RESEARCH": "research",
    "CREATIVE": "chat",
    "TRANSLATION": "translation",
}


def check_constraints(model_key: str, required_constraints: dict[str, Any]) -> tuple[bool, str]:
    """Check if model satisfies all mandatory constraints."""
    if model_key not in MODELS:
        return False, f"Model '{model_key}' not registered."
    
    spec = MODELS[model_key]
    model_constraints = spec.get("constraints", {})
    
    for req_key, req_val in required_constraints.items():
        val = model_constraints.get(req_key)
        if req_val is True and not val:
            return False, f"Model '{model_key}' lacks constraint '{req_key}'."
        if isinstance(req_val, int) and isinstance(val, int) and val < req_val:
            return False, f"Model '{model_key}' context ({val}) < required ({req_val})."

    return True, "OK"

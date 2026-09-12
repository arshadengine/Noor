"""
brain/resolvers/base.py
─────────────────────────────────────────────────────
Abstract Base Class for Resource Resolvers.
Defines ResourceType enum, match confidence calculation, and resolution payload.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any


class ResourceType(Enum):
    URL = "url"
    APPLICATION = "application"
    FILE = "file"
    FOLDER = "folder"
    SETTINGS = "settings"
    UNKNOWN = "unknown"


class BaseResourceResolver(ABC):
    """Abstract base class for modular resource resolvers."""

    @abstractmethod
    def match(self, target: str) -> float:
        """
        Evaluate target string and return a confidence score between 0.0 and 1.0.
        0.0 = no match, 1.0 = exact confident match.
        """
        pass

    @abstractmethod
    def resolve(self, target: str) -> Dict[str, Any]:
        """
        Resolve target and return payload dict:
        {
            "resource_type": ResourceType,
            "confidence": float,
            "resolved_target": str,
            "action": str,
            "metadata": dict
        }
        """
        pass

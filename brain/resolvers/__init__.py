"""
brain/resolvers/
─────────────────────────────────────────────────────
Modular ResourceResolver Pipeline for Noor.
Provides two-stage classification and confidence scoring across
URLs, Applications, Files, Folders, and Settings.
"""

from brain.resolvers.base import BaseResourceResolver, ResourceType
from brain.resolvers.manager import ResourceResolverManager

__all__ = ["BaseResourceResolver", "ResourceType", "ResourceResolverManager"]

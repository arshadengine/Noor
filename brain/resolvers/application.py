"""
brain/resolvers/application.py
─────────────────────────────────────────────────────
Application Resource Resolver.
Resolves desktop application names, aliases, multi-tag categories, and installed GUI software.
"""

from typing import Dict, Any
from brain.resolvers.base import BaseResourceResolver, ResourceType
from brain.system.discovery import get_application_by_query


class ApplicationResolver(BaseResourceResolver):
    """Resource resolver for desktop applications and GUI software."""

    def match(self, target: str) -> float:
        app = get_application_by_query(target)
        if app:
            t_clean = target.lower().strip()
            name_lower = app["name"].lower()
            exe_lower = app["exe_name"].lower()
            if t_clean in (name_lower, exe_lower, app["app_id"]):
                return 0.98
            return 0.90
        return 0.0

    def resolve(self, target: str) -> Dict[str, Any]:
        app = get_application_by_query(target)
        confidence = self.match(target)

        if app:
            return {
                "resource_type": ResourceType.APPLICATION,
                "confidence": confidence,
                "resolved_target": app["path"],
                "action": "launch_app",
                "metadata": {
                    "app_name": app["name"],
                    "exe_name": app["exe_name"],
                    "category": app["category"]
                }
            }

        return {
            "resource_type": ResourceType.UNKNOWN,
            "confidence": 0.0,
            "resolved_target": target,
            "action": "none",
            "metadata": {}
        }

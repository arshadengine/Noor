"""
brain/resolvers/settings.py
─────────────────────────────────────────────────────
Settings Resource Resolver.
Resolves Windows System Settings requests to native ms-settings: URIs.
Handles variations like "windows settings", "window setting", "settings app", "bluetooth".
"""

from typing import Dict, Any
from brain.resolvers.base import BaseResourceResolver, ResourceType


class SettingsResolver(BaseResourceResolver):
    """Resource resolver for Windows Settings and system configurations."""

    SETTINGS_MAP = {
        "settings": "ms-settings:",
        "setting": "ms-settings:",
        "windows settings": "ms-settings:",
        "windows setting": "ms-settings:",
        "window settings": "ms-settings:",
        "window setting": "ms-settings:",
        "system settings": "ms-settings:",
        "system setting": "ms-settings:",
        "settings app": "ms-settings:",
        "bluetooth": "ms-settings:bluetooth",
        "wifi": "ms-settings:network-wifi",
        "wi-fi": "ms-settings:network-wifi",
        "network": "ms-settings:network-status",
        "sound": "ms-settings:sound",
        "volume": "ms-settings:sound",
        "display": "ms-settings:display",
        "battery": "ms-settings:batterysaver",
        "storage": "ms-settings:storagesense",
    }

    def match(self, target: str) -> float:
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        if t_clean in self.SETTINGS_MAP or any(s in t_clean for s in self.SETTINGS_MAP):
            return 0.96
        return 0.0

    def resolve(self, target: str) -> Dict[str, Any]:
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        confidence = self.match(target)

        uri = "ms-settings:"
        for key, val in self.SETTINGS_MAP.items():
            if key in t_clean:
                uri = val
                break

        return {
            "resource_type": ResourceType.SETTINGS,
            "confidence": confidence,
            "resolved_target": uri,
            "action": "open_settings",
            "metadata": {
                "settings_uri": uri
            }
        }

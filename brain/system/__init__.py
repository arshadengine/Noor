"""
brain/system/
─────────────────────────────────────────────────────
System Telemetry, Incremental App Discovery, and Workspace Scoping.
"""

from brain.system.monitor import get_system_state, start_system_monitor
from brain.system.discovery import scan_and_register_applications, get_application_by_query
from brain.system.workspace import get_active_workspace, set_active_workspace

__all__ = [
    "get_system_state",
    "start_system_monitor",
    "scan_and_register_applications",
    "get_application_by_query",
    "get_active_workspace",
    "set_active_workspace"
]

"""
brain/tools/registry.py
─────────────────────────────────────────────────────
Central Tool Registry Gateway.
All OS actions (opening apps, reading/writing files, deleting files, process execution)
pass through this registry to enforce risk assessment and safety guardrails.
"""

import os
from enum import Enum
from typing import Callable, Any, Dict
from brain.memory import log_agent_action


class RiskLevel(Enum):
    LOW = "low"            # Auto-execute (e.g. read file, open app, get status)
    MEDIUM = "medium"      # Execute with audit log (e.g. write file, create folder)
    HIGH = "high"          # Intercept & estimate impact (e.g. delete file, close app)
    CRITICAL = "critical"  # Mandatory User Confirmation (e.g. mass delete, format, shutdown)


class ToolRegistry:
    """Central Gateway managing all registered tools and their execution policies."""

    _tools: Dict[str, Dict[str, Any]] = {}

    _initialized = False

    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            cls._initialized = True
            register_default_tools()

    @classmethod
    def register(cls, name: str, risk_level: RiskLevel, func: Callable, description: str = ""):
        """Register a tool into the global registry."""
        cls._tools[name] = {
            "name": name,
            "risk_level": risk_level,
            "func": func,
            "description": description
        }

    @classmethod
    def get_tool(cls, name: str) -> Dict[str, Any] | None:
        cls._ensure_initialized()
        return cls._tools.get(name)

    @classmethod
    def execute(cls, name: str, kwargs: dict = None, confirmed: bool = False) -> dict:
        """
        Execute a tool through the security pipeline.
        Returns a result dict: {"status": "success" | "confirmation_required" | "error", "output": ..., "impact_summary": ...}
        """
        cls._ensure_initialized()
        if kwargs is None:
            kwargs = {}

        tool = cls.get_tool(name)
        if not tool:
            return {"status": "error", "output": f"Tool '{name}' not registered."}

        risk = tool["risk_level"]
        func = tool["func"]

        # Guardrails check for HIGH risk operations
        from brain.tools.guardrails import evaluate_action_impact
        if risk == RiskLevel.HIGH and not confirmed:
            impact_summary = evaluate_action_impact(name, kwargs)
            return {
                "status": "confirmation_required",
                "output": f"⚠️ Action '{name}' requires confirmation: {impact_summary}",
                "impact_summary": impact_summary
            }

        try:
            log_agent_action("ToolRegistry", f"Executing tool '{name}' (Risk: {risk.name})")
            result = func(**kwargs)
            return {"status": "success", "output": result}
        except Exception as e:
            err_msg = f"❌ Error executing tool '{name}': {e}"
            log_agent_action("ToolRegistry", f"Tool '{name}' failed", str(e))
            return {"status": "error", "output": err_msg}


def register_default_tools():
    """Register standard OS agent tools into ToolRegistry."""
    from brain.system.discovery import get_application_by_query
    from brain.tools.launcher import launch_application
    from brain.tools.filesystem import find_and_rank_files
    from brain.system.monitor import get_system_state
    from brain.knowledge.graph import add_knowledge_edge

    def _open_app(app_name: str):
        app = get_application_by_query(app_name)
        if app:
            res = launch_application(app["executable_path"], app["display_name"])
            try:
                add_knowledge_edge("User", "User", "OPENED_APP", app["display_name"], "Application")
            except Exception:
                pass
            return res
        return f"⚠️ Application '{app_name}' not found."

    def _open_file(query: str):
        matches = find_and_rank_files(query, limit=1)
        if matches:
            top = matches[0]
            try:
                import os
                os.startfile(top["filepath"])
                add_knowledge_edge("User", "User", "OPENED_FILE", top["filename"], "File")
                return f"Opened file: {top['filepath']}"
            except Exception as e:
                return f"❌ Failed to open file {top['filepath']}: {e}"
        return f"⚠️ No matching file found for query '{query}'."

    def _delete_file(path: str):
        if os.path.exists(path):
            try:
                os.remove(path)
                return f"Deleted file: {path}"
            except Exception as e:
                return f"❌ Failed to delete {path}: {e}"
        return f"⚠️ Target '{path}' does not exist."

    ToolRegistry.register("open_app", RiskLevel.LOW, _open_app, "Open desktop application")
    ToolRegistry.register("open_file", RiskLevel.LOW, _open_file, "Find and open file")
    ToolRegistry.register("get_system_status", RiskLevel.LOW, get_system_state, "Get hardware and process status")
    ToolRegistry.register("delete_file", RiskLevel.HIGH, _delete_file, "Delete file or folder")

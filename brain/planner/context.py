"""
brain/planner/context.py
─────────────────────────────────────────────────────
Planning Context Gatherer for Noor.
Collects active workspace, active window, running apps, tool availability, and system state.
"""

from datetime import datetime
from brain.planner.schemas import PlanningContext
def gather_planning_context(user_query: str = "") -> PlanningContext:
    """Gather live runtime context to inform TaskPlanner decision-making."""
    try:
        from brain.system.workspace import get_active_workspace, is_developer_mode_active
        active_ws = get_active_workspace()
        dev_mode = is_developer_mode_active()
    except Exception:
        active_ws = "D:\\Noor"
        dev_mode = False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    running_apps = []
    active_win = "Unknown"

    try:
        from brain.system.monitor import get_running_process_names, get_active_window_title
        running_apps = get_running_process_names()
        active_win = get_active_window_title() or "Unknown"
    except Exception:
        pass

    tools_available = [
        "launcher", "filesystem", "browser", "terminal", "system",
        "settings", "voice", "vision", "knowledge_graph"
    ]

    sys_state = {
        "developer_mode": dev_mode,
        "platform": "windows"
    }

    return PlanningContext(
        conversation_summary="",
        active_workspace=active_ws,
        active_window=active_win,
        running_apps=running_apps,
        available_tools=tools_available,
        user_preferences={"default_browser": "chrome", "editor": "code"},
        system_state=sys_state,
        current_time=now_str
    )

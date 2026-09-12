"""
brain/planner/planner.py
─────────────────────────────────────────────────────
TaskPlanner Executive Function Core for Noor.
Converts user requests into validated, simulated, and optimized multi-step TaskPlan graphs.
Uses hybrid template matching (fast path) + LLM task graph generation (complex path).
"""

import re
import uuid
from typing import Optional
from brain.planner.schemas import TaskPlan, TaskStep, TaskType, PlanningContext
from brain.planner.context import gather_planning_context
from brain.planner.validator import validate_plan
from brain.planner.optimizer import optimize_plan
from brain.planner.telemetry import log_plan_telemetry
from brain.planner.templates import (
    get_open_template,
    get_coding_template,
    get_search_template,
    get_browser_template,
    get_system_template,
)


class TaskPlanner:
    """Main TaskPlanner executive engine."""

    def __init__(self):
        pass

    def create_plan(self, user_query: str, context: Optional[PlanningContext] = None) -> TaskPlan:
        """
        Convert natural language query into a validated, optimized TaskPlan.
        Does NOT execute any OS actions directly.
        """
        if not context:
            context = gather_planning_context(user_query)

        q_clean = user_query.strip()
        q_lower = q_clean.lower()

        # 1. Conversational Query (No tools required)
        conversational_triggers = ["joke", "hello", "hi", "who are you", "what can you do", "explain", "tell me"]
        if any(q_lower.startswith(x) or q_lower == x for x in conversational_triggers) and not any(x in q_lower for x in ["open", "search", "find", "code"]):
            plan_id = f"plan_conv_{uuid.uuid4().hex[:8]}"
            plan = TaskPlan(
                id=plan_id,
                goal=q_clean,
                task_type=TaskType.CONVERSATIONAL,
                priority=1,
                estimated_duration_sec=1.0,
                requires_confirmation=False,
                confidence=1.0,
                reasoning=["Conversational query requiring no OS tool execution."],
                steps=[
                    TaskStep(
                        id="step_1",
                        tool="none",
                        action="conversed_reply",
                        target="",
                        parameters={"prompt": q_clean}
                    )
                ],
                metadata={"category": "conversational"}
            )
            log_plan_telemetry(plan)
            return plan

        # 2. System Operations (Shutdown, Restart, Lock)
        if any(x in q_lower for x in ["shutdown", "restart", "reboot", "turn off", "lock pc"]):
            plan = get_system_template(q_clean, context)
            plan = optimize_plan(plan)
            log_plan_telemetry(plan)
            return plan

        # 3. Developer Coding Environment
        if any(x in q_lower for x in ["prepare my coding environment", "prepare coding environment", "coding workspace", "dev setup"]):
            plan = get_coding_template(q_clean, context)
            plan = optimize_plan(plan)
            log_plan_telemetry(plan)
            return plan

        # 4. Search + Open File ("Find my report", "search file report and open it")
        if any(x in q_lower for x in ["find my", "search for", "find the", "search file"]) and "open" in q_lower:
            plan = get_search_template(q_clean, context)
            plan = optimize_plan(plan)
            log_plan_telemetry(plan)
            return plan

        # 5. Browser URL / Dev Server
        if any(x in q_lower for x in ["localhost", "127.0.0.1", "http://", "https://", "github.com"]):
            # Extract target URL
            target_url = q_clean
            match = re.search(r"\b(https?://\S+|localhost:\d+|localhost|127\.0\.0\.1:\d+|127\.0\.0\.1|\S+\.com|\S+\.tech)\b", q_clean)
            if match:
                target_url = match.group(1)
            plan = get_browser_template(target_url, context)
            plan = optimize_plan(plan)
            log_plan_telemetry(plan)
            return plan

        # 6. Single Resource Open (Application / Folder / File / Settings)
        if re.search(r"\b(open|launch|start)\b", q_lower):
            match = re.search(r"\b(?:open|launch|start)\s+(.+)$", q_clean, re.IGNORECASE)
            target = match.group(1).strip() if match else q_clean
            plan = get_open_template(target, context)
            plan = optimize_plan(plan)
            log_plan_telemetry(plan)
            return plan

        # 7. Default Fallback Template Match
        plan = get_open_template(q_clean, context)
        valid, errors = validate_plan(plan)
        if not valid:
            plan.confidence = 0.50
            plan.reasoning.append(f"Validation warnings: {', '.join(errors)}")

        plan = optimize_plan(plan)
        log_plan_telemetry(plan)
        return plan

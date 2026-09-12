"""
brain/planner/parser.py
─────────────────────────────────────────────────────
Task Graph & LLM Response Parser.
Converts raw text or JSON structures into TaskPlan steps.
"""

import json
import re
from typing import List, Dict, Any
from brain.planner.schemas import TaskStep


def parse_llm_plan_response(res_text: str) -> List[TaskStep]:
    """Parse structured JSON plan array from LLM response."""
    steps: List[TaskStep] = []
    clean_text = res_text.strip()

    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```json\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text)

    try:
        data = json.loads(clean_text)
        raw_steps = data.get("steps", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

        for i, s in enumerate(raw_steps):
            step = TaskStep(
                id=s.get("id", f"step_{i+1}"),
                tool=s.get("tool", "launcher"),
                action=s.get("action", "open_application"),
                target=s.get("target", ""),
                parameters=s.get("parameters", {}),
                preconditions=s.get("preconditions", []),
                success_conditions=s.get("success_conditions", []),
                depends_on=s.get("depends_on", []),
                parallel=s.get("parallel", False),
                timeout_sec=float(s.get("timeout_sec", 30.0))
            )
            steps.append(step)
    except Exception as e:
        print(f"[Planner Parser Note] JSON parse fallback: {e}")

    return steps

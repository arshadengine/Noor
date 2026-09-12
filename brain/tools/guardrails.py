"""
brain/tools/guardrails.py
─────────────────────────────────────────────────────
Guardrail Policy Engine & Impact Estimator.
Evaluates tool operations against risk policies and calculates
recursive file counts or process impact before execution.
"""

import os
from pathlib import Path
from brain.tools.registry import RiskLevel


class GuardrailPolicy:
    """Policy engine enforcing confirmation prompts and impact estimations."""

    @staticmethod
    def evaluate(tool_name: str, risk_level: RiskLevel, kwargs: dict, confirmed: bool = False) -> dict:
        """Evaluate if an action can auto-execute or requires user confirmation."""
        # Low and Medium risk auto-pass
        if risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM):
            return {"status": "approved"}

        # If user explicitly confirmed in prompt/turn, allow execution
        if confirmed:
            return {"status": "approved"}

        # High or Critical risk actions without prior confirmation trigger impact estimation
        impact_summary = GuardrailPolicy._calculate_impact(tool_name, kwargs)
        return {
            "status": "confirmation_required",
            "impact_summary": impact_summary,
            "tool_name": tool_name,
            "kwargs": kwargs,
            "risk_level": risk_level.value
        }

    @staticmethod
    def _calculate_impact(tool_name: str, kwargs: dict) -> str:
        """Calculate exact file counts, target process names, or power action impact."""
        path_arg = kwargs.get("path") or kwargs.get("target") or kwargs.get("filepath")
        
        if tool_name in ("delete_file", "delete_folder", "remove_directory"):
            if path_arg and os.path.exists(path_arg):
                path_obj = Path(path_arg)
                if path_obj.is_dir():
                    file_count = sum(len(files) for _, _, files in os.walk(path_arg))
                    dir_count = sum(len(dirs) for _, dirs, _ in os.walk(path_arg))
                    return (
                        f"⚠️ Danger: This action will recursively delete folder '{path_obj.name}' "
                        f"containing {file_count:,} files and {dir_count:,} subdirectories. Proceed?"
                    )
                else:
                    size_kb = path_obj.stat().st_size / 1024
                    return f"⚠️ Warning: This will permanently delete file '{path_obj.name}' ({size_kb:.1f} KB). Proceed?"
            return f"⚠️ Warning: Destructive delete requested for target '{path_arg}'. Proceed?"

        if tool_name in ("kill_process", "taskkill"):
            process_name = kwargs.get("process_name") or path_arg or "process"
            return f"⚠️ Warning: Force stopping process '{process_name}' may result in unsaved data loss. Proceed?"

        if tool_name in ("shutdown_system", "restart_system"):
            return "⚠️ Critical: This action will reboot/shutdown your computer. Proceed?"

        return f"⚠️ Security Check: Action '{tool_name}' requires your explicit confirmation to proceed."

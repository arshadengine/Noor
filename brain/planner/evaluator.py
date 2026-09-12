"""
brain/planner/evaluator.py
─────────────────────────────────────────────────────
Post-Execution Evaluator & Honest Response Synthesizer for Noor.
Evaluates overall plan goal achievement and generates honest, non-hallucinated status summaries
split cleanly into Verified (Confirmed), Attempted (Unverified), and Failed actions.
"""

from brain.planner.schemas_execution import ExecutionReport, ExecutionStatus


class PostExecutionEvaluator:
    """Evaluates ExecutionReport and synthesizes honest user responses."""

    @staticmethod
    def evaluate_and_synthesize(report: ExecutionReport) -> ExecutionReport:
        """
        Synthesize honest natural language response from ExecutionReport.
        Strictly categorizes actions into Verified, Attempted, and Failed.
        Never hallucinates fake unverified sub-actions.
        """
        report.verified_summary = []
        report.attempted_summary = []
        report.failed_summary = []

        for step_res in report.step_results:
            target_display = step_res.target or step_res.action

            if step_res.status == ExecutionStatus.VERIFIED:
                lvl = step_res.evidence.verification_level.value.upper()
                pid_info = f" (PID {step_res.evidence.process_id})" if step_res.evidence.process_id else ""
                report.verified_summary.append(f"Opened/Executed '{target_display}' [{lvl} Verified{pid_info}]")

            elif step_res.status == ExecutionStatus.PARTIALLY_VERIFIED:
                report.attempted_summary.append(f"Dispatched '{target_display}', process running but window focus unconfirmed.")

            elif step_res.status == ExecutionStatus.FAILED:
                err = step_res.error_message or "Unknown failure"
                report.failed_summary.append(f"Failed to execute '{target_display}': {err}")

            elif step_res.status == ExecutionStatus.SKIPPED:
                report.attempted_summary.append(f"Skipped '{target_display}' due to failed precondition.")

        # Build honest conversational synthesis response
        lines = []

        if report.overall_status == "FULLY_COMPLETE":
            lines.append(f"Goal completed: **{report.goal}** 🚀\n")
        elif report.overall_status == "PARTIALLY_COMPLETE":
            lines.append(f"Goal partially completed: **{report.goal}** ⚠️\n")
        else:
            lines.append(f"Goal execution failed: **{report.goal}** ❌\n")

        if report.verified_summary:
            lines.append("**Verified Actions:**")
            for item in report.verified_summary:
                lines.append(f"  ✅ {item}")
            lines.append("")

        if report.attempted_summary:
            lines.append("**Attempted / Unverified Actions:**")
            for item in report.attempted_summary:
                lines.append(f"  ⚠️ {item}")
            lines.append("")

        if report.failed_summary:
            lines.append("**Failed Actions:**")
            for item in report.failed_summary:
                lines.append(f"  ❌ {item}")
            lines.append("")

        report.synthesized_response = "\n".join(lines).strip()
        return report

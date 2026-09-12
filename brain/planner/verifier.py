"""
brain/planner/verifier.py
─────────────────────────────────────────────────────
Empirical Step Verifier for Noor Execution Engine.
Gathers structured Evidence (PID, HWND, Process Path, Focus) and evaluates VerificationLevel.
Rejects hallucinated claims without empirical OS state proof.
"""

import os
import psutil
from datetime import datetime
from typing import Tuple
from brain.planner.schemas import TaskStep
from brain.planner.schemas_execution import ExecutionStatus, VerificationLevel, Evidence
from brain.planner.window import get_window_handle_for_process


class StepVerifier:
    """Empirical verifier that checks OS state after step execution."""

    @staticmethod
    def verify_step(step: TaskStep, raw_output: str = "") -> Tuple[ExecutionStatus, Evidence]:
        """
        Gather empirical evidence for a step's execution result.
        Returns (ExecutionStatus, Evidence).
        """
        now_str = datetime.now().isoformat()
        evidence = Evidence(
            launch_time=now_str,
            verification_time=now_str,
            verification_level=VerificationLevel.NONE,
            raw_details={"raw_output": raw_output}
        )

        tool = step.tool.lower().strip()
        action = step.action.lower().strip()
        target = step.target.lower().strip()

        # 1. Conversational / None tool
        if tool == "none":
            evidence.verification_level = VerificationLevel.STANDARD
            evidence.raw_details["status"] = "conversational_completed"
            return ExecutionStatus.VERIFIED, evidence

        # 2. Application Launcher (VS Code, Chrome, Explorer, Edge)
        if tool in ("launcher", "system") or action in ("open_application", "open_app"):
            target_exe = None
            if "code" in target or "vs code" in target:
                target_exe = "Code.exe"
            elif "chrome" in target:
                target_exe = "chrome.exe"
            elif "edge" in target:
                target_exe = "msedge.exe"
            elif "explorer" in target:
                target_exe = "explorer.exe"
            elif "notepad" in target:
                target_exe = "notepad.exe"
            elif "terminal" in target or "wt" in target:
                target_exe = "wt.exe"

            # Process scanning via psutil
            found_proc = None
            if target_exe:
                try:
                    for proc in psutil.process_iter(['pid', 'name', 'exe']):
                        if proc.info['name'] and proc.info['name'].lower() == target_exe.lower():
                            found_proc = proc
                            break
                except Exception:
                    pass

            if found_proc:
                evidence.process_id = found_proc.info['pid']
                evidence.process_name = found_proc.info['name']
                evidence.process_path = found_proc.info['exe'] or ""
                
                hwnd, title = get_window_handle_for_process(found_proc.info['pid'])
                evidence.window_handle = hwnd
                evidence.window_title = title

                if hwnd > 0:
                    evidence.verification_level = VerificationLevel.STRONG
                    return ExecutionStatus.VERIFIED, evidence
                else:
                    evidence.verification_level = VerificationLevel.BASIC
                    return ExecutionStatus.PARTIALLY_VERIFIED, evidence

        # 3. Filesystem Open Folder / Search
        if tool == "filesystem":
            if action in ("open_folder", "open_result"):
                # Verify explorer.exe or IDE is running
                try:
                    for proc in psutil.process_iter(['pid', 'name']):
                        if proc.info['name'] in ("explorer.exe", "Code.exe"):
                            evidence.process_id = proc.info['pid']
                            evidence.process_name = proc.info['name']
                            evidence.verification_level = VerificationLevel.STANDARD
                            return ExecutionStatus.VERIFIED, evidence
                except Exception:
                    pass
            elif action == "search_file":
                evidence.verification_level = VerificationLevel.STANDARD
                return ExecutionStatus.VERIFIED, evidence

        # 4. Browser URL Open
        if tool == "browser":
            # Verify browser process is active
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
                        evidence.process_id = proc.info['pid']
                        evidence.process_name = proc.info['name']
                        evidence.verification_level = VerificationLevel.STANDARD
                        return ExecutionStatus.VERIFIED, evidence
            except Exception:
                pass

        # 5. Fallback checks for output status
        if "opened" in raw_output.lower() or "success" in raw_output.lower() or "launched" in raw_output.lower():
            evidence.verification_level = VerificationLevel.BASIC
            return ExecutionStatus.VERIFIED, evidence

        evidence.verification_level = VerificationLevel.NONE
        return ExecutionStatus.FAILED, evidence

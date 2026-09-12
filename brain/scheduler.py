"""
brain/scheduler.py
─────────────────────────────────────────────────────
Noor's Automation Scheduler.

Runs in a background thread and triggers scheduled tasks based on time
or intervals, executing them via Noor's brain.
"""

from __future__ import annotations

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.memory import (
    get_automation_tasks, update_automation_task_last_run,
    log_agent_action
)
from brain.llm import simple_query

# Keep track of running scheduler thread
_scheduler_thread = None
_stop_event = threading.Event()


def scheduler_loop():
    """Background loop that evaluates and triggers tasks."""
    print("[Noor Scheduler] Background Automation Scheduler started.")
    log_agent_action("Scheduler", "Automation Scheduler started.")
    
    while not _stop_event.is_set():
        try:
            tasks = get_automation_tasks()
            now = datetime.utcnow()
            
            for t in tasks:
                if t["status"] != "active":
                    continue
                    
                task_id = t["id"]
                desc = t["task_description"]
                interval = t["interval_seconds"]
                trigger_time = t["trigger_time"]
                last_run_str = t["last_run"]
                
                last_run = None
                if last_run_str:
                    try:
                        last_run = datetime.fromisoformat(last_run_str)
                    except ValueError:
                        pass
                
                should_trigger = False
                
                # Case 1: Interval-based trigger
                if interval:
                    if not last_run or (now - last_run) >= timedelta(seconds=interval):
                        should_trigger = True
                        
                # Case 2: Time-based trigger (HH:MM)
                elif trigger_time:
                    current_time_str = now.strftime("%H:%M")
                    if current_time_str == trigger_time:
                        # Only run once per day
                        if not last_run or (now - last_run) >= timedelta(hours=23):
                            should_trigger = True
                            
                if should_trigger:
                    trigger_task(task_id, desc)
                    
        except Exception as e:
            print(f"[Noor Scheduler] Error in loop: {e}")
            
        # Sleep for 10 seconds before checking again
        _stop_event.wait(timeout=10.0)


def trigger_task(task_id: int, desc: str) -> None:
    """Execute a task using Noor's brain."""
    print(f"[Noor Scheduler] Triggering task {task_id}: '{desc}'")
    log_agent_action("Scheduler", f"Triggering task: '{desc}'")
    
    # Update last run first to prevent double triggers
    update_automation_task_last_run(task_id)
    
    # Run in a separate thread so it doesn't block the main scheduler loop
    t = threading.Thread(
        target=_run_task_execution,
        args=(task_id, desc),
        name=f"NoorTask_{task_id}",
        daemon=True
    )
    t.start()


def _run_task_execution(task_id: int, desc: str) -> None:
    """Run the task query and save the result."""
    try:
        system_prompt = (
            "You are Noor's background Automation Agent.\n"
            "You are executing the following scheduled task:\n"
            f"'{desc}'\n\n"
            "Perform the task. If it requires writing a note, checking files, or logging information, do so.\n"
            "Keep your output factual, concise, and clear. Respond with a summary of what you did."
        )
        
        prompt = f"Perform scheduled task: {desc}"
        response = simple_query(prompt, system_prompt)
        
        print(f"[Noor Scheduler] Task {task_id} completed: {response[:100]}...")
        log_agent_action("Scheduler", f"Completed task: '{desc}'", response[:200])
        
        # If task is a reminder or note, we can also play a chime or speak a brief summary
        if "remind" in desc.lower() or "speak" in desc.lower() or "tell me" in desc.lower():
            try:
                from brain.voice import speak_text
                import ctypes
                audio_path = speak_text(f"Task reminder: {response}")
                if audio_path and os.path.exists(audio_path):
                    audio_path_abs = os.path.abspath(audio_path)
                    ctypes.windll.winmm.mciSendStringW(f'open "{audio_path_abs}" type mpegvideo alias task_play', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW('play task_play wait', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW('close task_play', None, 0, 0)
            except Exception as voice_err:
                print(f"[Noor Scheduler] Failed to speak task reminder: {voice_err}")
                
    except Exception as e:
        print(f"[Noor Scheduler] Failed to execute task {task_id}: {e}")
        log_agent_action("Scheduler", f"Failed task {task_id}", str(e))


def start_scheduler() -> None:
    """Start the background scheduler thread."""
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return
        
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=scheduler_loop, name="NoorScheduler", daemon=True)
    _scheduler_thread.start()


def stop_scheduler() -> None:
    """Stop the background scheduler thread."""
    global _scheduler_thread
    _stop_event.set()
    if _scheduler_thread:
        _scheduler_thread.join(timeout=3.0)
        _scheduler_thread = None
        print("[Noor Scheduler] Scheduler stopped.")

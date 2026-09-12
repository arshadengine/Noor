"""
test_scheduler.py
Verify task scheduling, execution triggers, and deletion logic.
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent))

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from brain.memory import init_db, add_automation_task, get_automation_tasks, delete_automation_task
from brain.scheduler import start_scheduler, stop_scheduler

def test_scheduler_lifecycle():
    print("[Test] Initializing database...")
    init_db()
    
    print("[Test] Registering a 2-second interval task...")
    task_desc = "Test automation: Print hello in logs"
    
    # Clean up old test tasks if any exist
    tasks = get_automation_tasks()
    for t in tasks:
        if t["task_description"] == task_desc:
            delete_automation_task(t["id"])
            
    task_id = add_automation_task(task_desc, interval_seconds=2)
    print(f"Task registered with ID: {task_id}")
    
    # Retrieve to verify it is registered
    tasks = get_automation_tasks()
    matching = [t for t in tasks if t["id"] == task_id]
    assert len(matching) == 1
    assert matching[0]["task_description"] == task_desc
    assert matching[0]["interval_seconds"] == 2
    assert matching[0]["last_run"] is None
    print("[Test] ✅ Task registration verified.")
    
    print("[Test] Starting scheduler background thread...")
    start_scheduler()
    
    # Wait for the scheduler to trigger the task (checks every 10s by default, but let's wait 12s to guarantee it fires)
    print("Waiting 12 seconds for background trigger...")
    time.sleep(12.0)
    
    # Stop scheduler first so we can safely query
    print("Stopping scheduler...")
    stop_scheduler()
    
    # Verify the task ran and last_run was updated
    tasks_after = get_automation_tasks()
    matching_after = [t for t in tasks_after if t["id"] == task_id]
    assert len(matching_after) == 1
    print(f"Task last run timestamp: {matching_after[0]['last_run']}")
    assert matching_after[0]["last_run"] is not None
    print("[Test] ✅ Task execution and last run update verified.")
    
    print("[Test] Deleting task...")
    delete_automation_task(task_id)
    tasks_final = get_automation_tasks()
    matching_final = [t for t in tasks_final if t["id"] == task_id]
    assert len(matching_final) == 0
    print("[Test] ✅ Task deletion verified.")

if __name__ == "__main__":
    print("=== Automation Scheduler Test Suite ===")
    test_scheduler_lifecycle()
    print("=== All Scheduler tests completed successfully! ===")

"""
brain/planner/history.py
─────────────────────────────────────────────────────
Persistent Task History Store for Noor (Phase 2.3.3).
Persists task plans, execution reports, durations, success rates, and evidence to SQLite (task_history in noor.db).
Provides analytical queries for debugging and continuous learning.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from brain.planner.schemas import TaskPlan
from brain.planner.schemas_execution import ExecutionReport

DB_PATH = Path("D:/Noor/data/noor.db")


class TaskHistoryManager:
    """Manages SQLite persistent task execution history."""

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls):
        """Initialize task_history table in SQLite database."""
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
                    status TEXT NOT NULL,
                    success_rate REAL NOT NULL,
                    verified_count INTEGER NOT NULL,
                    attempted_count INTEGER NOT NULL,
                    failed_count INTEGER NOT NULL,
                    plan_json TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @classmethod
    def record_task_history(cls, plan: TaskPlan, report: ExecutionReport) -> bool:
        """Persist a completed or failed task execution report into SQLite."""
        try:
            cls.init_db()
            now_str = datetime.now().isoformat()
            total_steps = max(1, len(report.step_results))
            verified_count = len(report.verified_summary)
            attempted_count = len(report.attempted_summary)
            failed_count = len(report.failed_summary)

            success_rate = round((verified_count / float(total_steps)) * 100.0, 1)

            with cls._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO task_history (
                        task_id, goal, task_type, started_at, finished_at,
                        duration_sec, status, success_rate, verified_count,
                        attempted_count, failed_count, plan_json, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan.id,
                    plan.goal,
                    plan.task_type.value if hasattr(plan.task_type, "value") else str(plan.task_type),
                    now_str,
                    now_str,
                    report.total_duration_sec,
                    report.overall_status,
                    success_rate,
                    verified_count,
                    attempted_count,
                    failed_count,
                    json.dumps(plan.to_dict()),
                    json.dumps(report.to_dict())
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"[TaskHistory Note] SQLite save exception: {e}")
            return False

    @classmethod
    def query_task_history(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Query recent task execution history records."""
        try:
            cls.init_db()
            with cls._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, goal, task_type, started_at, finished_at,
                           duration_sec, status, success_rate, verified_count,
                           attempted_count, failed_count, created_at
                    FROM task_history
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[TaskHistory Note] SQLite query exception: {e}")
            return []

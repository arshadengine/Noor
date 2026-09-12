"""
brain/runtime/history.py
─────────────────────────────────────────────────────
Persistent Task History Store for Noor Runtime (Phase 2.3.3).
Persists task plans, execution reports, durations, success rates, tags, and evidence to SQLite (task_history in noor.db).
Provides analytical queries (get_stats_today, query_by_tag, get_most_used_tools).
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
    """Manages SQLite persistent task execution history and search analytics."""

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls):
        """Initialize task_history table in SQLite database with tags column."""
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
                    tags_json TEXT DEFAULT '[]',
                    plan_json TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration check for existing task_history tables without tags_json column
            cursor.execute("PRAGMA table_info(task_history)")
            cols = [row[1] for row in cursor.fetchall()]
            if "tags_json" not in cols:
                cursor.execute("ALTER TABLE task_history ADD COLUMN tags_json TEXT DEFAULT '[]'")

            conn.commit()

    @classmethod
    def record_task_history(cls, plan: TaskPlan, report: ExecutionReport, tags: Optional[List[str]] = None) -> bool:
        """Persist a completed or failed task execution report into SQLite."""
        try:
            cls.init_db()
            now_str = datetime.now().isoformat()
            total_steps = max(1, len(report.step_results))
            verified_count = len(report.verified_summary)
            attempted_count = len(report.attempted_summary)
            failed_count = len(report.failed_summary)

            success_rate = round((verified_count / float(total_steps)) * 100.0, 1)

            # Deduce tags from goal if empty
            if not tags:
                tags = []
                g_lower = plan.goal.lower()
                if "code" in g_lower or "vs" in g_lower:
                    tags.append("coding")
                if "chrome" in g_lower or "url" in g_lower or "browser" in g_lower:
                    tags.append("browser")
                if "download" in g_lower or "folder" in g_lower:
                    tags.append("workspace")

            tags_json = json.dumps(tags)

            with cls._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO task_history (
                        task_id, goal, task_type, started_at, finished_at,
                        duration_sec, status, success_rate, verified_count,
                        attempted_count, failed_count, tags_json, plan_json, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    tags_json,
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
                           attempted_count, failed_count, tags_json, created_at
                    FROM task_history
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                res = []
                for row in rows:
                    r_dict = dict(row)
                    r_dict["tags"] = json.loads(r_dict.get("tags_json", "[]"))
                    res.append(r_dict)
                return res
        except Exception as e:
            print(f"[TaskHistory Note] SQLite query exception: {e}")
            return []

    @classmethod
    def query_by_tag(cls, tag: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search task history by tag (e.g. 'coding', 'browser')."""
        all_hist = cls.query_task_history(limit=100)
        matching = [h for h in all_hist if tag.lower() in [t.lower() for t in h.get("tags", [])]]
        return matching[:limit]

    @classmethod
    def get_stats_today(cls) -> Dict[str, Any]:
        """Return task execution statistics for today."""
        all_hist = cls.query_task_history(limit=200)
        today_str = datetime.now().strftime("%Y-%m-%d")

        today_tasks = [h for h in all_hist if h.get("created_at", "").startswith(today_str)]
        total = len(today_tasks)
        succeeded = len([h for h in today_tasks if h.get("status") == "FULLY_COMPLETE"])
        failed = len([h for h in today_tasks if h.get("status") == "FAILED"])

        avg_dur = round(sum(h.get("duration_sec", 0.0) for h in today_tasks) / float(total), 2) if total > 0 else 0.0

        return {
            "total_tasks_today": total,
            "succeeded_count": succeeded,
            "failed_count": failed,
            "avg_duration_sec": avg_dur,
        }

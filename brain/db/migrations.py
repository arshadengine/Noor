"""
brain/db/migrations.py
─────────────────────────────────────────────────────
Manages versioned database migrations for Noor.
"""

from brain.db.database import get_db
from brain.db.schema import init_db_schema


def run_migrations() -> None:
    """Run all schema migrations cleanly."""
    init_db_schema()
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);")
        cursor = conn.execute("SELECT MAX(version) FROM schema_version;")
        row = cursor.fetchone()
        current_version = row[0] if row and row[0] is not None else 0

        if current_version < 1:
            conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (1);")
            print("[Noor DB] Migrated database to version 1.")

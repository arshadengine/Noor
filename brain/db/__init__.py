"""
brain/db/
─────────────────────────────────────────────────────
Central Database Layer for Noor.
Provides thread-safe SQLite connection factory and schema migrations.
"""

from brain.db.database import get_db, DB_PATH
from brain.db.schema import init_db_schema

__all__ = ["get_db", "DB_PATH", "init_db_schema"]

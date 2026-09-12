"""
brain/db/database.py
─────────────────────────────────────────────────────
Thread-safe SQLite connection factory for Noor.
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

DB_PATH = Path(os.getenv("DB_PATH", "D:/Noor/data/noor.db"))


def get_db() -> sqlite3.Connection:
    """Return a thread-safe connection to the SQLite database with Row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

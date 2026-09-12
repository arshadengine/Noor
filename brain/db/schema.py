"""
brain/db/schema.py
─────────────────────────────────────────────────────
Defines and initializes all SQLite database tables for Noor.
"""

from brain.db.database import get_db


def init_db_schema() -> None:
    """Create all database tables and indexes if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content     TEXT NOT NULL,
                mode        TEXT DEFAULT 'friend',
                timestamp   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id          TEXT PRIMARY KEY,
                content     TEXT NOT NULL,
                importance  INTEGER DEFAULT 1 CHECK(importance BETWEEN 1 AND 5),
                tags        TEXT DEFAULT '[]',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                source      TEXT DEFAULT 'conversation',
                confidence  REAL DEFAULT 1.0,
                metadata    TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id          TEXT PRIMARY KEY,
                filename    TEXT NOT NULL,
                filepath    TEXT,
                ingested_at TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS corrections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern     TEXT UNIQUE,
                correction  TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS graph_nodes (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                source_id   TEXT NOT NULL,
                target_id   TEXT NOT NULL,
                relation    TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relation),
                FOREIGN KEY (source_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES graph_nodes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agent_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name  TEXT NOT NULL,
                action      TEXT NOT NULL,
                result      TEXT,
                timestamp   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS automation_tasks (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                task_description    TEXT NOT NULL,
                trigger_time        TEXT,
                interval_seconds    INTEGER,
                last_run            TEXT,
                status              TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed'))
            );

            CREATE TABLE IF NOT EXISTS proactive_suggestions (
                id              TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                content         TEXT NOT NULL,
                event_type      TEXT NOT NULL,
                status          TEXT DEFAULT 'unread' CHECK(status IN ('unread', 'read', 'accepted', 'dismissed')),
                action_data     TEXT,
                created_at      TEXT NOT NULL
            );

            -- Phase 2.2: Universal Tool & OS Intelligence Tables --

            CREATE TABLE IF NOT EXISTS installed_applications (
                app_id       TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                exe_name     TEXT NOT NULL,
                path         TEXT NOT NULL,
                category     TEXT DEFAULT 'utility',
                tags         TEXT DEFAULT '[]',
                aliases      TEXT DEFAULT '[]',
                last_scanned TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS file_index (
                id            TEXT PRIMARY KEY,
                filename      TEXT NOT NULL,
                filepath      TEXT NOT NULL UNIQUE,
                file_type     TEXT DEFAULT 'file',
                last_modified TEXT NOT NULL,
                size_bytes    INTEGER DEFAULT 0,
                tags          TEXT DEFAULT '[]',
                workspace     TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS system_telemetry_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_percent  REAL,
                ram_percent  REAL,
                battery_pct  REAL,
                active_app   TEXT,
                timestamp    TEXT NOT NULL
            );

            -- Indexes for fast lookup --
            CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conv_time    ON conversations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_proactive_status ON proactive_suggestions(status);
            CREATE INDEX IF NOT EXISTS idx_installed_apps_name ON installed_applications(name);
            CREATE INDEX IF NOT EXISTS idx_file_index_filename ON file_index(filename);
            CREATE INDEX IF NOT EXISTS idx_file_index_workspace ON file_index(workspace);
        """)
    print("[Noor DB] Database schema initialized successfully.")

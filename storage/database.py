"""
storage/database.py

A thin wrapper around sqlite3 that:
  1. Owns the single on-disk connection for the whole app.
  2. Creates every table the modules need, in one place, on first run.
  3. Exposes simple execute/query helpers so individual modules don't each
     re-implement cursor/commit/error-handling boilerplate.

Every module's storage file (e.g. modules/notes/storage.py) imports `db`
from here rather than opening its own connection. SQLite only safely
supports one writer at a time, so a single shared connection avoids
"database is locked" errors that crop up when multiple connections in the
same process try to write concurrently.
"""

import sqlite3
import threading

from core.config import DB_PATH, ensure_app_dirs


class Database:
    """Singleton-style wrapper around one sqlite3 connection.

    check_same_thread=False is required because PySide6 signals can fire
    storage calls from a different Qt thread than the one that opened the
    connection (e.g. a QTimer callback). We protect every actual write with
    a lock to keep access serialized and safe.
    """

    def __init__(self):
        ensure_app_dirs()
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._create_schema()

    # -- low level helpers --------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/DELETE statement and commit it."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def executemany(self, sql: str, seq_of_params) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.executemany(sql, seq_of_params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return all rows as a list of sqlite3.Row
        (dict-like access by column name)."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchone()

    def last_insert_id(self) -> int:
        return self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def close(self):
        with self._lock:
            self._conn.close()

    # -- schema ---------------------------------------------------------

    def _create_schema(self):
        """Every table for every module, created idempotently. Keeping all
        schema definitions in one place makes it easy to see the full data
        model at a glance and avoids import-order problems between
        modules."""
        with self._lock:
            self._conn.executescript(
                """
                -- Generic key/value settings (theme, sidebar width, last
                -- opened module, hotkeys, etc.)
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                -- Notes module
                CREATE TABLE IF NOT EXISTS notes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT NOT NULL DEFAULT '',
                    body       TEXT NOT NULL DEFAULT '',
                    color      TEXT NOT NULL DEFAULT '#7c8cff',
                    tags       TEXT NOT NULL DEFAULT '',
                    pinned     INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Calculator history
                CREATE TABLE IF NOT EXISTS calc_history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    expression TEXT NOT NULL,
                    result     TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                -- Calendar: a note/reminder attached to a specific date
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_date TEXT NOT NULL,      -- 'YYYY-MM-DD'
                    title      TEXT NOT NULL,
                    note       TEXT NOT NULL DEFAULT '',
                    remind_at  TEXT,                -- 'YYYY-MM-DD HH:MM' or NULL
                    created_at TEXT NOT NULL
                );

                -- Clipboard history
                CREATE TABLE IF NOT EXISTS clipboard_items (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    content    TEXT NOT NULL,
                    category   TEXT NOT NULL DEFAULT 'general',
                    pinned     INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                -- Favorites (manual list, replacing browser bookmarks)
                CREATE TABLE IF NOT EXISTS favorites (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT NOT NULL,
                    url        TEXT NOT NULL,
                    folder     TEXT NOT NULL DEFAULT 'General',
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                -- Quick links (toolbar-style shortcuts, user-ordered)
                CREATE TABLE IF NOT EXISTS quick_links (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    title     TEXT NOT NULL,
                    url       TEXT NOT NULL,
                    icon      TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0
                );

                -- Todo list
                CREATE TABLE IF NOT EXISTS todos (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT NOT NULL,
                    done        INTEGER NOT NULL DEFAULT 0,
                    priority    TEXT NOT NULL DEFAULT 'normal',  -- low/normal/high
                    due_date    TEXT,                             -- 'YYYY-MM-DD' or NULL
                    sort_order  INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL
                );

                -- Chat history (mocked AI for now; schema is provider-agnostic)
                CREATE TABLE IF NOT EXISTS chat_conversations (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT NOT NULL DEFAULT 'New conversation',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role            TEXT NOT NULL,   -- 'user' or 'assistant'
                    content         TEXT NOT NULL,
                    created_at      TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE
                );
                """
            )
            self._conn.commit()


# Module-level singleton. Every other file does `from storage.database import db`.
db = Database()

"""
Thread-safe SQLite database manager for Archimedes.
Uses threading.local() for connection-per-thread safety.
"""
import sqlite3
import threading
import os
import logging

import config

logger = logging.getLogger(__name__)

_local = threading.local()


def get_connection():
    """
    Returns a thread-local SQLite connection.
    Creates the data directory and database file if they don't exist.
    """
    if not hasattr(_local, "connection") or _local.connection is None:
        os.makedirs(config.DATABASE_DIR, exist_ok=True)
        _local.connection = sqlite3.connect(config.DATABASE_PATH)
        _local.connection.row_factory = sqlite3.Row
        _local.connection.execute("PRAGMA journal_mode=WAL")
        _local.connection.execute("PRAGMA foreign_keys=ON")
    return _local.connection


def close_connection():
    """Closes the thread-local connection if it exists."""
    if hasattr(_local, "connection") and _local.connection is not None:
        _local.connection.close()
        _local.connection = None


def init_db():
    """
    Initializes the database schema.
    Creates tables if they do not already exist.
    Safe to call multiple times (idempotent).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            report_json TEXT NOT NULL,
            project_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        )
    """)

    # Index for fast history lookups per user
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id
        ON research_sessions(user_id, created_at DESC)
    """)

    # ── API Cache ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            results_json TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            UNIQUE(query_hash, source)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cache_lookup
        ON api_cache(query_hash, source)
    """)

    # ── Bookmarks ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            paper_title TEXT NOT NULL,
            paper_json TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, paper_title)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookmarks_user
        ON bookmarks(user_id, created_at DESC)
    """)

    # ── Projects / Workspaces ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_user
        ON projects(user_id, created_at DESC)
    """)

    # Add project_id column to research_sessions if it doesn't exist
    # (for existing databases that already have the table)
    try:
        cursor.execute("ALTER TABLE research_sessions ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    logger.info("Database initialized successfully.")

"""SQLite connection, schema and migrations.

The schema is Postgres-compatible on purpose: when this moves to Supabase,
only this module changes. Nothing outside ``core`` opens a connection.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager

from core import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE,
    ui_language   TEXT NOT NULL DEFAULT 'en-IN',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lessons (
    id       TEXT PRIMARY KEY,
    subject  TEXT NOT NULL,
    grade    INTEGER NOT NULL,
    title_en TEXT NOT NULL,
    payload  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    lesson_id   TEXT NOT NULL,
    segment_id  TEXT,
    status      TEXT NOT NULL,
    score       REAL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, lesson_id, segment_id)
);

CREATE TABLE IF NOT EXISTS translations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    source_text TEXT NOT NULL,
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    output_text TEXT NOT NULL,
    provider    TEXT NOT NULL,
    latency_ms  INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    event_name  TEXT NOT NULL,
    props       TEXT,
    lang        TEXT,
    session_id  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_name_time ON events(event_name, created_at);
CREATE INDEX IF NOT EXISTS idx_events_lang ON events(lang);
CREATE INDEX IF NOT EXISTS idx_translations_pair ON translations(source_lang, target_lang);
"""


def connect() -> sqlite3.Connection:
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Transactional connection: commits on success, always closes."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Idempotent schema creation. Safe to call on every app start."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def ensure_local_user(ui_language: str = config.DEFAULT_LANG) -> int:
    """The single local learner used until real auth exists (Phase 5).

    Returns the user id, creating the row once and reusing it after that.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (name, email, ui_language) VALUES (?, ?, ?)",
            ("Local learner", "local@demo.in", ui_language),
        )
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("local@demo.in",)
        ).fetchone()
        return int(row["id"])


def set_ui_language(user_id: int, lang: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET ui_language = ? WHERE id = ?", (lang, user_id))


def now_ms() -> int:
    """Monotonic-ish wall clock in milliseconds, used for latency numbers."""
    return int(time.time() * 1000)


def get_cached_translation(source_text: str, source_lang: str, target_lang: str) -> dict | None:
    """Newest matching row for this exact pair, or None. The DB-level cache."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT output_text, provider, latency_ms FROM translations"
            " WHERE source_text = ? AND source_lang = ? AND target_lang = ?"
            " ORDER BY id DESC LIMIT 1",
            (source_text, source_lang, target_lang),
        ).fetchone()
    return dict(row) if row else None


def save_translation(
    source_text: str,
    source_lang: str,
    target_lang: str,
    output_text: str,
    provider: str,
    latency_ms: int,
    user_id: int | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO translations"
            " (user_id, source_text, source_lang, target_lang, output_text, provider, latency_ms)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, source_text, source_lang, target_lang, output_text, provider, latency_ms),
        )


def recent_translations(limit: int = 8) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT source_text, source_lang, target_lang, output_text, provider,"
            " latency_ms, created_at FROM translations ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def translation_stats() -> dict:
    """Counts the Translate page shows under the result: real, cache, mock."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM translations").fetchone()["n"]
        avg = conn.execute("SELECT AVG(latency_ms) AS v FROM translations").fetchone()["v"]
        by_provider = conn.execute(
            "SELECT provider, COUNT(*) AS n FROM translations GROUP BY provider"
        ).fetchall()
    return {
        "total": int(total),
        "avg_latency_ms": int(avg) if avg else 0,
        "by_provider": {row["provider"]: int(row["n"]) for row in by_provider},
    }


def upsert_progress(
    user_id: int,
    lesson_id: str,
    segment_id: str | None,
    status: str,
    score: float | None = None,
) -> None:
    """Insert or update one progress row.

    Lesson-level rows store ``segment_id = ""`` rather than NULL, because SQLite
    treats NULLs as distinct and the UNIQUE constraint would never fire.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO progress (user_id, lesson_id, segment_id, status, score)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(user_id, lesson_id, segment_id) DO UPDATE SET"
            " status = excluded.status, score = excluded.score,"
            " updated_at = datetime('now')",
            (user_id, lesson_id, segment_id or "", status, score),
        )


def lesson_progress(user_id: int, lesson_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status, score, updated_at FROM progress"
            " WHERE user_id = ? AND lesson_id = ? AND segment_id = ''"
            " ORDER BY id DESC LIMIT 1",
            (user_id, lesson_id),
        ).fetchone()
    return dict(row) if row else None


def progress_summary(user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n,"
            " SUM(CASE WHEN status = 'quiz_passed' THEN 1 ELSE 0 END) AS passed,"
            " AVG(score) AS avg_score"
            " FROM progress WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return {
        "lessons_touched": int(row["n"] or 0),
        "quiz_passed": int(row["passed"] or 0),
        "avg_score": round(float(row["avg_score"] or 0) * 100),
    }


def reset_db() -> None:
    """Delete the database file. Dev and tests only — never called by pages."""
    path = config.db_path()
    if path.exists():
        path.unlink()

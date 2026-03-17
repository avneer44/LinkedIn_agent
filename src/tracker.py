"""
tracker.py - SQLite database for tracking seen and sent jobs.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id      TEXT PRIMARY KEY,
                title       TEXT,
                company     TEXT,
                location    TEXT,
                apply_url   TEXT,
                score       INTEGER,
                reason      TEXT,
                emailed     INTEGER DEFAULT 0,
                seen_at     TEXT
            )
        """)
        conn.commit()


def is_seen(job_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return row is not None


def mark_seen(job_id: str, title: str, company: str, location: str,
              apply_url: str, score: int = 0, reason: str = "") -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO jobs (job_id, title, company, location, apply_url, score, reason, seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, title, company, location, apply_url, score, reason,
              datetime.utcnow().isoformat()))
        conn.commit()


def mark_emailed(job_ids: list[str]) -> None:
    with _connect() as conn:
        conn.executemany("UPDATE jobs SET emailed = 1 WHERE job_id = ?",
                         [(jid,) for jid in job_ids])
        conn.commit()


def is_emailed(job_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT emailed FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return bool(row and row["emailed"])


def get_all_seen_ids() -> set:
    with _connect() as conn:
        rows = conn.execute("SELECT job_id FROM jobs").fetchall()
        return {row["job_id"] for row in rows}


def get_recent_jobs(limit: int = 50) -> list:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT job_id, title, company, location, apply_url, score, reason, emailed, seen_at "
            "FROM jobs ORDER BY seen_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_stats() -> dict:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        emailed = conn.execute("SELECT COUNT(*) FROM jobs WHERE emailed = 1").fetchone()[0]
        return {"total_seen": total, "total_emailed": emailed}

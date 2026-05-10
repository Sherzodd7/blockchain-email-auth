# app/database/db_handler.py
# ─────────────────────────────────────────────────────────────────────────────
# SQLite persistence layer.
# Table: messages  (id, email, message, hash, signature, tx_hash, status,
#                   trust_score, is_phishing, timestamp)
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import os
from datetime import datetime, timezone
from typing   import Optional

from config           import Config
from app.utils.logger import log


# ─── Schema ───────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER  PRIMARY KEY AUTOINCREMENT,
    email        TEXT     NOT NULL,
    message      TEXT     NOT NULL,
    hash         TEXT     NOT NULL UNIQUE,
    signature    TEXT     NOT NULL,
    tx_hash      TEXT,
    status       TEXT     NOT NULL DEFAULT 'pending',
    trust_score  INTEGER  NOT NULL DEFAULT 100,
    is_phishing  INTEGER  NOT NULL DEFAULT 0,
    timestamp    TEXT     NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_email ON messages(email);
CREATE INDEX IF NOT EXISTS idx_messages_hash  ON messages(hash);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
"""


def _get_connection() -> sqlite3.Connection:
    """Open a database connection with row_factory for dict-style access."""
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")   # better concurrency
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist yet."""
    with _get_connection() as conn:
        conn.executescript(DDL)
    log.info("Database initialised → %s", Config.DB_PATH)


# ─── Write ────────────────────────────────────────────────────────────────────

def save_message(
    email       : str,
    message     : str,
    hash_str    : str,
    signature   : str,
    tx_hash     : str,
    status      : str = "valid",
    trust_score : int = 100,
    is_phishing : bool = False,
) -> int:
    """
    Insert a new message record.
    Returns the newly created row id.
    """
    ts = datetime.now(timezone.utc).isoformat()
    sql = """
        INSERT INTO messages
            (email, message, hash, signature, tx_hash, status,
             trust_score, is_phishing, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _get_connection() as conn:
        cursor = conn.execute(sql, (
            email, message, hash_str, signature, tx_hash,
            status, trust_score, int(is_phishing), ts,
        ))
        row_id = cursor.lastrowid
    log.debug("Message saved  id=%d  email=%s  status=%s", row_id, email, status)
    return row_id


def update_status(hash_str: str, status: str) -> None:
    """Update the status of an existing message by hash."""
    with _get_connection() as conn:
        conn.execute(
            "UPDATE messages SET status = ? WHERE hash = ?",
            (status, hash_str)
        )
    log.debug("Status updated  hash=%s…  status=%s", hash_str[:12], status)


# ─── Read ─────────────────────────────────────────────────────────────────────

def get_all_messages(limit: int = 100, offset: int = 0) -> list[dict]:
    """Return all messages ordered by timestamp desc."""
    sql = """
        SELECT id, email, message, hash, signature, tx_hash,
               status, trust_score, is_phishing, timestamp
        FROM   messages
        ORDER  BY id DESC
        LIMIT  ? OFFSET ?
    """
    with _get_connection() as conn:
        rows = conn.execute(sql, (limit, offset)).fetchall()
    return [dict(r) for r in rows]


def get_message_by_hash(hash_str: str) -> Optional[dict]:
    """Return a single message by its SHA-256 hash, or None."""
    sql = "SELECT * FROM messages WHERE hash = ? LIMIT 1"
    with _get_connection() as conn:
        row = conn.execute(sql, (hash_str,)).fetchone()
    return dict(row) if row else None


def get_messages_by_email(email: str) -> list[dict]:
    """Return all messages from a given sender email."""
    sql = "SELECT * FROM messages WHERE email = ? ORDER BY id DESC"
    with _get_connection() as conn:
        rows = conn.execute(sql, (email,)).fetchall()
    return [dict(r) for r in rows]


def count_messages() -> int:
    """Total number of stored messages."""
    with _get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]


def count_valid_messages_by_email(email: str) -> int:
    """Used for trust-score computation."""
    with _get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM messages WHERE email = ? AND status = 'valid'",
            (email,)
        ).fetchone()[0]


def count_phishing_by_email(email: str) -> int:
    """Count phishing-flagged messages from a sender."""
    with _get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM messages WHERE email = ? AND is_phishing = 1",
            (email,)
        ).fetchone()[0]


def get_stats() -> dict:
    """Dashboard statistics."""
    with _get_connection() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        valid     = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'valid'").fetchone()[0]
        invalid   = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'invalid'").fetchone()[0]
        tampered  = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'tampered'").fetchone()[0]
        phishing  = conn.execute("SELECT COUNT(*) FROM messages WHERE is_phishing = 1").fetchone()[0]
    return {
        "total"   : total,
        "valid"   : valid,
        "invalid" : invalid,
        "tampered": tampered,
        "phishing": phishing,
    }

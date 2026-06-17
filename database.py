"""
database.py — SQLite ticket database for banking support system.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Optional

DB_PATH = "banking_support.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id   TEXT PRIMARY KEY,
            user_name   TEXT NOT NULL,
            message     TEXT NOT NULL,
            category    TEXT NOT NULL,
            sentiment   TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'open',
            response    TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ticket_logs (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id   TEXT NOT NULL,
            action      TEXT NOT NULL,
            details     TEXT,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        );
    """)
    conn.commit()
    conn.close()


def create_ticket(user_name, message, category, sentiment, response):
    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO tickets
           (ticket_id, user_name, message, category, sentiment, status, response, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)""",
        (ticket_id, user_name, message, category, sentiment, response, now, now),
    )
    cursor.execute(
        "INSERT INTO ticket_logs (ticket_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (ticket_id, "created", f"Category: {category} | Sentiment: {sentiment}", now),
    )
    conn.commit()
    conn.close()
    return ticket_id


def get_ticket(ticket_id):
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_ticket_status(ticket_id, status):
    valid = {"open", "in_progress", "resolved"}
    if status not in valid:
        return False
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
        (status, now, ticket_id),
    )
    if cursor.rowcount == 0:
        conn.close()
        return False
    cursor.execute(
        "INSERT INTO ticket_logs (ticket_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (ticket_id, "status_update", f"New status: {status}", now),
    )
    conn.commit()
    conn.close()
    return True


def get_all_tickets():
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ticket_logs(ticket_id):
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT * FROM ticket_logs WHERE ticket_id = ? ORDER BY timestamp ASC", (ticket_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    total       = cursor.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    open_count  = cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
    resolved    = cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='resolved'").fetchone()[0]
    in_progress = cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0]
    by_category = cursor.execute("SELECT category, COUNT(*) as cnt FROM tickets GROUP BY category").fetchall()
    by_sentiment= cursor.execute("SELECT sentiment, COUNT(*) as cnt FROM tickets GROUP BY sentiment").fetchall()
    conn.close()
    return {
        "total": total, "open": open_count,
        "in_progress": in_progress, "resolved": resolved,
        "by_category":  {r["category"]: r["cnt"]  for r in by_category},
        "by_sentiment": {r["sentiment"]: r["cnt"] for r in by_sentiment},
    }

init_db()
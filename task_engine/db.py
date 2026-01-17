import sqlite3
from datetime import datetime
from pathlib import Path
from task_engine.domain import Task
import os
import json

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("TASK_DB_PATH", BASE_DIR / "tasks.db"))
EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,

    stream_id TEXT NOT NULL,
    stream_type TEXT NOT NULL,

    stream_version INTEGER NOT NULL,

    event_type TEXT NOT NULL,
    event_payload TEXT NOT NULL,
    event_metadata TEXT NOT NULL,

    occurred_at TEXT NOT NULL,

    UNIQUE(stream_id, stream_version)
);
"""

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""

        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            state_changed_at TEXT NOT NULL
        ) 

    """)
    
     # Event store (source of truth)
    cur.execute(EVENTS_TABLE_SQL)

    conn.commit()
    conn.close()
# IMPORTANT:
# `tasks` is a derived projection.
# It must NEVER be the source of truth.
# All lifecycle decisions must come from events.
def save_task(task):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO tasks
        (task_id, state, created_at, state_changed_at)
        VALUES (?, ?, ?, ?)
    """, (
        task.id,
        task.state,
        task.created_at.isoformat(),
        task.state_changed_at.isoformat()
    ))

    conn.commit()
    conn.close()


def rehydrate_task(task_id: str):
    events = load_events(task_id)

    if not events:
        return None, 0

    task = Task(task_id)

    for event in events:
        task.apply(event)

    return task, task.version

def load_task(task_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM tasks WHERE task_id = ?",
        (task_id,)
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    from task_engine.app import Task

    task = Task(row["task_id"])
    task.state = row["state"]
    task.created_at = datetime.fromisoformat(row["created_at"])
    task.state_changed_at = datetime.fromisoformat(row["state_changed_at"])

    return task

def load_events(task_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT event_type, event_payload, event_metadata, stream_version
        FROM events
        WHERE stream_id = ?
        ORDER BY stream_version ASC
        """,
        (task_id,)
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "event_type": row["event_type"],
            "payload": json.loads(row["event_payload"]),
            "metadata": json.loads(row["event_metadata"]),
            "version": row["stream_version"],
        }
        for row in rows
    ]

class ConcurrencyError(Exception):
    pass


def append_event(
    *,
    stream_id: str,
    stream_type: str,
    expected_version: int,
    event_type: str,
    payload: dict,
    metadata: dict
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Get current stream version
        cur.execute(
            "SELECT MAX(stream_version) FROM events WHERE stream_id = ?",
            (stream_id,)
        )
        row = cur.fetchone()
        current_version = row[0] if row and row[0] is not None else 0

        if current_version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version}, found {current_version}"
            )

        next_version = current_version + 1

        cur.execute(
            """
            INSERT INTO events (
                stream_id,
                stream_type,
                stream_version,
                event_type,
                event_payload,
                event_metadata,
                occurred_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stream_id,
                stream_type,
                next_version,
                event_type,
                json.dumps(payload),
                json.dumps(metadata),
                datetime.now()
            )
        )

        conn.commit()
        return next_version

    finally:
        conn.close()
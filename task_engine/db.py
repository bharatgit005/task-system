import sqlite3
from datetime import datetime
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("TASK_DB_PATH", BASE_DIR / "tasks.db"))


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

    conn.commit()
    conn.close()

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


    
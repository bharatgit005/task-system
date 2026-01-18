from task_engine.app import apply_task_action, TaskActionRequest
from task_engine.domain import Task
import pytest
from fastapi import HTTPException
import os
from task_engine.db import DB_PATH
from task_engine.db import init_db, append_event, load_events
from task_engine import db
from datetime import datetime

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_tasks.db"
    monkeypatch.setenv("TASK_DB_PATH", str(test_db))
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield

#helper function
def create_task(task_id: str):
    now = datetime.utcnow().isoformat()
    append_event(
        stream_id=task_id,
        stream_type="TASK",
        expected_version=0,
        event_type="TaskCreated",
        payload={
            "state": "CREATED",
            "created_at": now
        },
        metadata={
            "actor": "system"
        }
    )

def test_cannot_skip_lc():
    create_task("200")
    with pytest.raises(Exception):
        apply_task_action("200",TaskActionRequest(requested_action="start_progress", actor_id="USER"))

def test_completed_task_is_immutable():
    create_task("200")
    # TASK_STORE["2"] = task

    # Move task through valid lifecycle
    apply_task_action("200", TaskActionRequest(requested_action="submit_for_review", actor_id="USER"))
    apply_task_action("200", TaskActionRequest(requested_action="start_progress", actor_id="USER"))
    apply_task_action("200", TaskActionRequest(requested_action="complete_task", actor_id="USER"))
    
    # Attempt any further action (should fail)
    with pytest.raises(HTTPException):
        apply_task_action("200", TaskActionRequest(requested_action="start_progress", actor_id="USER"))

def test_user_cannot_archive():
    create_task("200")

    with pytest.raises(HTTPException):
        apply_task_action("200",TaskActionRequest(requested_action="archive_task", actor_id="USER"))

#nagetive testing
def test_unknown_actor_has_no_power():
    create_task("200")

    with pytest.raises(HTTPException):
        apply_task_action(
            "200",
            TaskActionRequest(
                requested_action="submit_for_review",
                actor_id="unknown_actor"
            )
        )

def test_unknown_action_is_rejected():
    create_task("200")

    with pytest.raises(HTTPException):
        apply_task_action(
            "200",
            TaskActionRequest(
                requested_action="delete_everything",
                actor_id="system"
            )
        )
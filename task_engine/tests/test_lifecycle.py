from task_engine.app import apply_task_action, TaskActionRequest, get_task_projection
from task_engine.domain import Task
import pytest
from fastapi import HTTPException
import os
from task_engine.db import DB_PATH
from task_engine.db import init_db, append_event, load_events, get_connection, project_task
from task_engine import db
from datetime import datetime
import uuid

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
        },
        idempotency_key=f"create-{task_id}-{uuid.uuid4()}",
        correlation_id=f"create-{task_id}"
    )

def cmd(action: str, actor: str):
    return TaskActionRequest(
        requested_action=action,
        actor_id=actor,
        idempotency_key=str(uuid.uuid4())
    )


def test_cannot_skip_lc():
    create_task("200")
    with pytest.raises(Exception):
        apply_task_action("200",cmd("start_progress", "USER"))

def test_completed_task_is_immutable():
    create_task("200")
    # TASK_STORE["2"] = task

    # Move task through valid lifecycle
    apply_task_action("200", cmd("submit_for_review","USER"))
    apply_task_action("200", cmd("start_progress", "USER"))
    apply_task_action("200", cmd("complete_task", "USER"))
    
    # Attempt any further action (should fail)
    with pytest.raises(HTTPException):
        apply_task_action("200", cmd("start_progress", "USER"))

def test_user_cannot_archive():
    create_task("200")

    with pytest.raises(HTTPException):
        apply_task_action("200",cmd("archive_task", "USER"))

#nagetive testing
def test_unknown_actor_has_no_power():
    create_task("200")

    with pytest.raises(HTTPException):
        apply_task_action(
            "200",
            cmd(
                "submit_for_review",
                "unknown_actor"
            )
        )

def test_unknown_action_is_rejected():
    create_task("200")

    with pytest.raises(HTTPException):
        apply_task_action(
            "200",
            cmd(
                "delete_everything",
                "system"
            )
        )

def test_projection_can_be_rebuilt_from_events(isolated_db):
    # Arrange
    create_task("p1")
    apply_task_action("p1", cmd("submit_for_review", "USER"))
    apply_task_action("p1", cmd("start_progress", "USER"))

    # Sanity: projection exists
    proj = get_task_projection("p1")
    assert proj["current_state"] == "IN_PROGRESS"

    # Act: destroy projection
    conn = get_connection()
    conn.execute("DELETE FROM task_projection")
    conn.commit()
    conn.close()

    # Rebuild
    events = load_events("p1")
    project_task("p1", events)

    # Assert
    rebuilt = get_task_projection("p1")
    assert rebuilt["current_state"] == "IN_PROGRESS"
    assert rebuilt["version"] == len(events)

def test_commands_do_not_depend_on_projection(isolated_db):
    create_task("p2")

    # Corrupt / remove projection
    conn = get_connection()
    conn.execute("DELETE FROM task_projection")
    conn.commit()
    conn.close()

    # Command must still work
    apply_task_action("p2", cmd("submit_for_review", "USER"))

    events = load_events("p2")
    assert events[-1]["event_type"] == "TaskTransitioned"

def test_duplicate_command_is_idempotent():
    create_task("id1")

    key = "same-key"

    apply_task_action(
        "id1",
        TaskActionRequest(
            requested_action="submit_for_review",
            actor_id="USER",
            idempotency_key=key
        )
    )

    apply_task_action(
        "id1",
        TaskActionRequest(
            requested_action="submit_for_review",
            actor_id="USER",
            idempotency_key=key
        )
    )

    events = load_events("id1")
    assert len(events) == 2  # TaskCreated + one transition

def test_events_share_correlation_id():
    create_task("c1")

    key = "cmd-1"

    apply_task_action(
        "c1",
        TaskActionRequest(
            requested_action="submit_for_review",
            actor_id="USER",
            idempotency_key=key
        )
    )

    events = load_events("c1")
    correlation_ids = {
        e["correlation_id"]
        for e in events
        if e["event_type"] != "TaskCreated"
    }

    assert len(correlation_ids) == 1
from task_engine.app import apply_task_action, TaskActionRequest, Task
import pytest
from fastapi import HTTPException
import os
from task_engine.db import DB_PATH
from task_engine.db import save_task, init_db
from task_engine import db

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_tasks.db"
    monkeypatch.setenv("TASK_DB_PATH", str(test_db))
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield


def test_cannot_skip_lc():

    with pytest.raises(Exception):
        apply_task_action("101",TaskActionRequest(requested_action="start_progress", actor_id="USER"))

def test_completed_task_is_immutable():
    task = Task("101")
    save_task(task)
    # TASK_STORE["2"] = task

    # Move task through valid lifecycle
    apply_task_action("101", TaskActionRequest(requested_action="submit_for_review", actor_id="USER"))
    apply_task_action("101", TaskActionRequest(requested_action="start_progress", actor_id="USER"))
    apply_task_action("101", TaskActionRequest(requested_action="complete_task", actor_id="USER"))
    
    # Attempt any further action (should fail)
    with pytest.raises(HTTPException):
        apply_task_action("101", TaskActionRequest(requested_action="start_progress", actor_id="USER"))

def test_user_cannot_archive():
    task = Task("101")
    save_task(task)

    with pytest.raises(HTTPException):
        apply_task_action("101",TaskActionRequest(requested_action="archive_task", actor_id="USER"))

#nagetive testing
def test_unknown_actor_has_no_power():
    task = Task("200")
    save_task(task)

    with pytest.raises(HTTPException):
        apply_task_action(
            "200",
            TaskActionRequest(
                requested_action="submit_for_review",
                actor_id="unknown_actor"
            )
        )

def test_unknown_action_is_rejected():
    task = Task("201")
    save_task(task)

    with pytest.raises(HTTPException):
        apply_task_action(
            "201",
            TaskActionRequest(
                requested_action="delete_everything",
                actor_id="system"
            )
        )
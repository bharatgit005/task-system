from task_engine.app import apply_task_action, TaskActionRequest, TASK_STORE, Task
import pytest
from fastapi import HTTPException

def setup_function():
    TASK_STORE.clear()


def test_cannot_skip_lc():
    task = Task("1")
    TASK_STORE["1"] = task

    with pytest.raises(Exception):
        apply_task_action("1",TaskActionRequest(requested_action="start_progress"))

def test_completed_task_is_immutable():
    task = Task("2")
    TASK_STORE["2"] = task

    # Move task through valid lifecycle
    apply_task_action("2", TaskActionRequest(requested_action="submit_for_review"))
    apply_task_action("2", TaskActionRequest(requested_action="start_progress"))
    apply_task_action("2", TaskActionRequest(requested_action="complete_task"))
    
    # Attempt any further action (should fail)
    with pytest.raises(HTTPException):
        apply_task_action("2", TaskActionRequest(requested_action="start_progress"))
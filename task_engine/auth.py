from typing import Set

# Canonical capability names
CREATE_TASK = "create_task"
SUBMIT_FOR_REVIEW = "submit_for_review"
START_PROGRESS = "start_progress"
COMPLETE_TASK = "complete_task"
ARCHIVE_TASK = "archive_task"


# Capability registry (single source of truth)
ACTION_CAPABILITIES = {
    "submit_for_review": SUBMIT_FOR_REVIEW,
    "start_progress": START_PROGRESS,
    "complete_task": COMPLETE_TASK,
    "archive_task": ARCHIVE_TASK,
}
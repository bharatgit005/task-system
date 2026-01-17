from datetime import datetime

class Task:
    def __init__(self, task_id: str):
        self.id = task_id
        self.state = None
        self.created_at = None
        self.state_changed_at = None
        self.version = 0   # derived from events

    def apply(self, event: dict):
        event_type = event["event_type"]
        payload = event["payload"]

        if event_type == "TaskCreated":
            self.state = payload["state"]
            self.created_at = datetime.fromisoformat(payload["created_at"])
            self.state_changed_at = self.created_at

        elif event_type == "TaskTransitioned":
            self.state = payload["to_state"]
            self.state_changed_at = datetime.fromisoformat(payload["occurred_at"])

        elif event_type in ("TransitionRejected", "CapabilityDenied"):
            # These are facts, but they do NOT change task state
            pass

        else:
            raise ValueError(f"Unknown event type: {event_type}")

        # version always advances on any event
        self.version = event["version"]
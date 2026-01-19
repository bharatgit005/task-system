from pydantic import BaseModel

class CreateTaskRequest(BaseModel):
    idempotency_key: str


class TaskActionRequest(BaseModel):
    requested_action: str
    actor_id: str
    idempotency_key: str
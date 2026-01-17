from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from task_engine.db import init_db, save_task, rehydrate_task, append_event, load_events
from contextlib import asynccontextmanager
from task_engine.capability_resolver import resolve_capabilities
from task_engine.auth import ACTION_CAPABILITIES
from task_engine.domain import Task


# data model
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (nothing needed yet)



# In memory store -  not using database yet!

# TASK_STORE = {}


#Lifecycle rules - important!!!

STATE_TRANSITIONS = {

    "CREATED":{
        "submit_for_review":"IN_REVIEW"
    },

    "IN_REVIEW":{
        "start_progress":"IN_PROGRESS"
    },
    
    "IN_PROGRESS":{
        "complete_task":"COMPLETED"
    },

    "COMPLETED":{},
    "ARCHIVED":{}

}
ACTION_PERMISSIONS = {
    "submit_for_review": "USER",
    "start_progress": "USER",
    "complete_task": "USER",
    "archive_task": "SYSTEM",
}
#API contracts

class TaskActionRequest(BaseModel):
    requested_action: str
    actor_id: str

class TaskActionResponse(BaseModel):
    task_id: str
    current_state: str
    state_changed_at: datetime
    is_immutable: bool
    next_allowed_actions: list[str]

# FASTAPI app

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#END points

@app.post("/tasks/{task_id}")
def create_task(task_id: str):
    task, _ = rehydrate_task(task_id) 
    if task:
        raise HTTPException(status_code=400, detail="task already exists")

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
   # Rehydrate to derive state
    task, _ = rehydrate_task(task_id)

    return{
        "task_id": task_id,
        "state": task.state

    }

@app.post("/tasks/{task_id}/actions",response_model=TaskActionResponse)
def apply_task_action(task_id: str, action: TaskActionRequest):
    # 1. Rehydrate from events (SOURCE OF TRUTH)
    task, version = rehydrate_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    
    current_state = task.state
    now = datetime.utcnow().isoformat()
    #auth logic
    actor_capabilities = resolve_capabilities(action.actor_id)
    required_capability = ACTION_CAPABILITIES.get(action.requested_action)

    if required_capability:
        if required_capability not in actor_capabilities:
            append_event(
                stream_id=task.id,
            stream_type="TASK",
            expected_version=version,
            event_type="CapabilityDenied",
            payload={
                "from_state": current_state,
                "attempted_action": action.requested_action,
                "occurred_at": now
            },
            metadata={
                "actor_id": action.actor_id
                }
            )
            raise HTTPException(status_code=403, detail="actor lack of required capability")
    
    #lifecycle logic
    allowed_actions = STATE_TRANSITIONS.get(current_state,{})
    if action.requested_action not in allowed_actions:
        append_event(
            stream_id=task.id,
            stream_type="TASK",
            expected_version=version,
            event_type="TransitionRejected",
            payload={
                "from_state": current_state,
                "attempted_action": action.requested_action,
                "occurred_at": now
            },
            metadata={
                "actor_id": action.actor_id
            }
        )
        raise HTTPException(status_code=400, detail=f"Action {action.requested_action} not allowed from state {current_state}")
    
    new_state = allowed_actions[action.requested_action]
    append_event(
        stream_id=task.id,
        stream_type="TASK",
        expected_version=version,
        event_type="TaskTransitioned",
        payload={
            "from_state": current_state,
            "to_state": new_state,
            "occurred_at": now
        },
        metadata={
            "actor_id": action.actor_id,
            "action": action.requested_action
        }
    )
    # 5. Rehydrate again to derive new state
    task, _ = rehydrate_task(task_id)

    next_allowed_actions = list(
        STATE_TRANSITIONS.get(task.state,{}).keys()
    )

    return TaskActionResponse(
        task_id=task.id,
        current_state=task.state,
        state_changed_at = task.state_changed_at,
        is_immutable=(task.state == "ARCHIVED"),
        next_allowed_actions = next_allowed_actions
    )

@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task, _ = rehydrate_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    return {
        "task_id": task.id,
        "current_state": task.state,
        "state_changed_at": task.state_changed_at.isoformat() if task.state_changed_at else None,
        "is_immutable": (task.state == "ARCHIVED"),
        "next_allowed_actions": list(
            STATE_TRANSITIONS.get(task.state,{}).keys()
        )
    }

@app.get("/tasks/{task_id}/events")
def get_task_events(task_id: str):
    events = load_events(task_id)

    if not events:
        raise HTTPException(status_code=404, detail="task not found")

    return {
        "task_id": task_id,
        "events": events
    }
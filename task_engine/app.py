from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from task_engine.db import init_db, save_task, load_task
from contextlib import asynccontextmanager

# data model
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (nothing needed yet)

class Task:
    def __init__(self, task_id: str):
        self.id = task_id
        self.state  = "CREATED"
        self.created_at = datetime.now()
        self.state_changed_at = self.created_at

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

#API contracts

class TaskActionRequest(BaseModel):
    requested_action: str

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
    existing = load_task(task_id)
    if existing:
        raise HTTPException(status_code=400, detail="task already exists")
    task = Task(task_id)
    save_task(task)

    return{
        "task_id": task_id,
        "state": task.state

    }

@app.post("/tasks/{task_id}/actions",response_model=TaskActionResponse)
def apply_task_action(task_id: str, action: TaskActionRequest):
    task = load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    
    current_state = task.state

    allowed_actions = STATE_TRANSITIONS.get(current_state,{})



    if action.requested_action not in allowed_actions:
        raise HTTPException(status_code=400, detail=f"Action {action.requested_action} not allowed from state {current_state}")
    
    new_state = allowed_actions[action.requested_action]
    task.state = new_state
    task.state_changed_at = datetime.now()
    save_task(task)
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
    task = load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    return {
        "task_id": task.id,
        "current_state": task.state,
        "state_changed_at": task.state_changed_at,
        "is_immutable": (task.state == "ARCHIVED"),
        "next_allowed_actions": list(
            STATE_TRANSITIONS.get(task.state,{}).keys()
        )
    }


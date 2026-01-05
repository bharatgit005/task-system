from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# data model

class Task:
    def __init__(self, task_id: str):
        self.id = task_id
        self.state  = "CREATED"
        self.created_at = datetime.now()
        self.state_changed_at = self.created_at

# In memory store -  not using database yet!

TASK_STORE = {}


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

app = FastAPI()
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
    if task_id in TASK_STORE:
        raise HTTPException(status_code=400, detail="task is already exists!")

    task = Task(task_id)
    TASK_STORE[task_id] = task

    return{
        "task_id":task.id,
        "state":task.state
    }

@app.post("/tasks/{task_id}/actions",response_model=TaskActionResponse)
def apply_task_action(task_id: str, action: TaskActionRequest):
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail=f"task with {task_id} does not exists")
    

    task = TASK_STORE[task_id]
    current_state = task.state

    allowed_actions = STATE_TRANSITIONS.get(current_state,{})



    if action.requested_action not in allowed_actions:
        raise HTTPException(status_code=400, detail=f"Action {action.requested_action} not allowed from state {current_state}")
    
    new_state = allowed_actions[action.requested_action]
    task.state = new_state
    task.state_changed_at = datetime.now()
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
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="Task not found")

    task = TASK_STORE[task_id]

    return {
        "task_id": task.id,
        "current_state": task.state,
        "state_changed_at": task.state_changed_at,
        "is_immutable": (task.state == "ARCHIVED"),
        "next_allowed_actions": list(
            STATE_TRANSITIONS.get(task.state,{}).keys()
        )
    }
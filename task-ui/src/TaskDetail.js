function TaskDetail(task, loading, onAction){
    if(!task){
        return <div>Select a Task</div>
    }
}

return (
    <div>
        <h3>Task {task.task_id}</h3>
        <p><strong>State:</strong>{task.current_state}</p>
        <p><strong>Last Changed:</strong>{task.state_changed_at}</p>

        {task.next_allowed_actions.map(action=>(
            <button key={action} onClick={()=>onAction(action)} disabled={loading}>
                {action}
            </button>
        )

        )
        }
        {loading && <p>processing..</p>}
    </div>
);
export default TaskDetail;
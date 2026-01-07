function TaskDetail({ task }) {
  if (!task) {
    return <div>Loading task...</div>
  }

  return (
    <div>
      <h3>Task {task.task_id}</h3>

      <p>
        <strong>State:</strong> {task.current_state}
      </p>

      <div>
        {Array.isArray(task.next_allowed_actions) &&
          task.next_allowed_actions.map((action) => (
            <button key={action}>{action}</button>
          ))}
      </div>
    </div>
  )
}

export default TaskDetail
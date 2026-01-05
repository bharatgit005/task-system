function TaskList({tasks, onSelect}){
    return(
        <div>
            <h3>Tasks</h3>
            <ul>
                {
                    tasks.map(task =>(
                        <li key={task.task_id}>
                            <button onClick={()=> onSelect(task)}>
                                Task {task.task_id} - {task.current_state}
                            </button>
                        </li>
                    )

                    )
                }
            </ul>
        </div>
    );
}
export default TaskList;
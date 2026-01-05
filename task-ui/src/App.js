import { useEffect, useState } from "react";
import TaskList from "./TaskList";
import TaskDetail from "./TaskDetail";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/tasks`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch tasks");
        return res.json();
      })
      .then(data => setTasks(data))
      .catch(err => setError(err.message));
  }, []);

  function sendAction(action) {
    if (!selectedTask) return;

    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/tasks/${selectedTask.task_id}/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ requested_action: action })
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(err => {
            throw new Error(err.detail);
          });
        }
        return res.json();
      })
      .then(updatedTask => {
        setSelectedTask(updatedTask);

        return fetch(`${API_BASE}/tasks`)
          .then(res => res.json())
          .then(setTasks);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }

  if (error) return <div>Error: {error}</div>;

  return (
    <div style={{ padding: "40px", fontFamily: "sans-serif" }}>
      <TaskList tasks={tasks} onSelect={setSelectedTask} />
      <TaskDetail task={selectedTask} loading={loading} onAction={sendAction} />
    </div>
  );
}

export default App;
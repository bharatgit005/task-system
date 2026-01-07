import { useEffect, useState } from "react"
import TaskDetail from "./TaskDetail"

function App() {
  const [task, setTask] = useState(null)

  useEffect(() => {
    fetch("http://127.0.0.1:8000/tasks/1")
      .then((res) => {
        if (!res.ok) {
          throw new Error("Failed to fetch task")
        }
        return res.json()
      })
      .then((data) => {
        setTask(data)
      })
      .catch((err) => {
        console.error(err)
      })
  }, [])

  return (
    <div>
      <h2>Task Viewer</h2>
      <TaskDetail task={task} />
    </div>
  )
}

export default App
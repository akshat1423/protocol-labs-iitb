"use client";

interface Task {
  task_id: string;
  title: string;
  status: string;
  plan: string[];
  created_at: number;
  completed_at: number | null;
  error: string | null;
}

interface TaskListProps {
  tasks: Task[];
  currentTaskId: string | null;
}

const statusColors: Record<string, string> = {
  discovered: "bg-gray-500",
  planning: "bg-yellow-500",
  executing: "bg-blue-500 animate-pulse",
  verifying: "bg-purple-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
  aborted: "bg-gray-600",
};

const statusLabels: Record<string, string> = {
  discovered: "Discovered",
  planning: "Planning",
  executing: "Executing",
  verifying: "Verifying",
  completed: "Completed",
  failed: "Failed",
  aborted: "Aborted",
};

export function TaskList({ tasks, currentTaskId }: TaskListProps) {
  return (
    <div className="bg-agent-card border border-agent-border rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-400 mb-3">TASKS</h2>

      {tasks.length === 0 ? (
        <p className="text-xs text-gray-600">No tasks yet. Agent is discovering...</p>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.task_id}
              className={`p-3 rounded border ${
                task.task_id === currentTaskId
                  ? "border-agent-accent bg-agent-accent/5"
                  : "border-agent-border"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-white truncate flex-1">{task.title}</span>
                <div className="flex items-center gap-1.5 ml-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${statusColors[task.status]}`} />
                  <span className="text-xs text-gray-400">{statusLabels[task.status]}</span>
                </div>
              </div>

              {task.plan.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {task.plan.map((step, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <span className="text-gray-600 shrink-0">{i + 1}.</span>
                      <span className="text-gray-400">{step}</span>
                    </div>
                  ))}
                </div>
              )}

              {task.error && (
                <p className="text-xs text-agent-red mt-1">{task.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

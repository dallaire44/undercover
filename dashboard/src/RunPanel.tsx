import { useState } from "react";
import { getLatestRun, startRun, type Run, type Todo } from "./api";
import { useLoad } from "./useLoad";

const TODO_LABELS: Record<Todo["status"], string> = {
  to_do: "To do",
  in_progress: "In progress",
  done: "Done",
  left_for_handler: "Left for a handler",
};
const FIRST_CAP = 5;

const claims = (count: number) =>
  count === 1 ? "1 claim" : `${String(count)} claims`;

function RunState({ run }: Readonly<{ run: Run }>) {
  if (run.status === "running") return <p>Running, up to {claims(run.cap)}</p>;
  if (run.status === "stopped") return <p>Stopped: {run.summary}</p>;
  return <p>Finished, {claims(run.claim_ids.length)} worked</p>;
}

function TodoList({ todos }: Readonly<{ todos: Todo[] }>) {
  if (!todos.length) return null;
  return (
    <ol className="todos" aria-label="To-do list">
      {todos.map((todo) => (
        <li key={todo.content}>
          <span className={`chip todo-${todo.status}`}>
            {TODO_LABELS[todo.status]}
          </span>
          <span>{todo.content}</span>
        </li>
      ))}
    </ol>
  );
}

/** Start a run of the agent on the queue, and follow the latest run. */
export function RunPanel({
  waiting,
  onStart,
}: Readonly<{ waiting: number; onStart: () => void }>) {
  const { data: run, reload } = useLoad(
    getLatestRun,
    (loaded) => loaded?.status === "running",
  );
  const [cap, setCap] = useState(FIRST_CAP);
  const running = run?.status === "running";
  const started = () => {
    void reload();
    onStart();
  };
  return (
    <section className="panel run" aria-labelledby="run-title">
      <h2 id="run-title">Agent run</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void startRun(cap).then(started, started);
        }}
      >
        <label>
          Claims to work{" "}
          <input
            type="number"
            min={1}
            max={Math.max(waiting, 1)}
            value={cap}
            onChange={(event) => {
              setCap(Number(event.target.value));
            }}
          />
        </label>
        <button type="submit" disabled={running || waiting === 0}>
          Work the queue
        </button>
      </form>
      {run && (
        <>
          <RunState run={run} />
          <TodoList todos={run.todos} />
          {run.status === "finished" && (
            <p className="summary">{run.summary}</p>
          )}
        </>
      )}
    </section>
  );
}

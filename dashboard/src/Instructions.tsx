import { api } from "./api";
import { useLoad } from "./useLoad";

export function Instructions() {
  const { data, error } = useLoad(api.getInstructions);
  if (error) return <p role="alert">The instructions could not be loaded.</p>;
  if (!data) return <p>Loading the instructions.</p>;
  return (
    <>
      <p>
        <a href="#/">Back to the queue</a>
      </p>
      <section className="panel" aria-labelledby="instructions-title">
        <h2 id="instructions-title">The agent's instructions</h2>
        <p className="muted">
          Read only. The agent fetches these at the start of every run.
        </p>
        <pre className="instructions">{data.text}</pre>
      </section>
    </>
  );
}

import { getInstructions } from "./api";
import { useLoad } from "./useLoad";

export function Instructions() {
  const { data: text, failed } = useLoad(getInstructions);
  if (failed) return <p>The instructions could not be loaded.</p>;
  return (
    <>
      <h1>Agent instructions</h1>
      <section className="panel" aria-label="The agent's instructions">
        <pre className="instructions">{text}</pre>
      </section>
    </>
  );
}

import { getInstructions } from "./api";
import { useLoad } from "./useLoad";

export function Instructions() {
  const { data: text, failed } = useLoad(getInstructions);
  return (
    <>
      <h1>Agent instructions</h1>
      <section className="panel" aria-label="Working a claim">
        <h2>Working a claim</h2>
        {failed ? (
          <p>The instructions could not be loaded.</p>
        ) : (
          <pre className="instructions">{text}</pre>
        )}
      </section>
    </>
  );
}

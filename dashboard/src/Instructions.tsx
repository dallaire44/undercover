import { getInstructions } from "./api";
import { useLoad } from "./useLoad";

const getClaimInstructions = () => getInstructions("claim");

export function Instructions() {
  const { data: text, failed } = useLoad(getClaimInstructions);
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

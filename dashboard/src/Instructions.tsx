import { useCallback } from "react";
import { getInstructions } from "./api";
import { useLoad } from "./useLoad";

function InstructionsPanel({
  agent,
  title,
}: Readonly<{ agent: "queue" | "claim"; title: string }>) {
  const { data: text, failed } = useLoad(
    useCallback(() => getInstructions(agent), [agent]),
  );
  return (
    <section className="panel" aria-label={title}>
      <h2>{title}</h2>
      {failed ? (
        <p>The instructions could not be loaded.</p>
      ) : (
        <pre className="instructions">{text}</pre>
      )}
    </section>
  );
}

export function Instructions() {
  return (
    <>
      <h1>Agent instructions</h1>
      <InstructionsPanel agent="queue" title="Running the queue" />
      <InstructionsPanel agent="claim" title="Working a claim" />
    </>
  );
}

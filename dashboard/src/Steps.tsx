import { useCallback } from "react";
import { api } from "./api";
import type { Step } from "./api";
import { useLoad } from "./useLoad";

const KINDS: Record<Step["kind"], string> = {
  message: "The agent says",
  tool_call: "Tool call",
  tool_result: "Tool result",
};

const FOLD_OVER = 160;

/** The agent is working while its last run has started and not finished. */
function running(steps: Step[]): boolean {
  return (
    steps.some((step) => step.text === "Agent started") &&
    steps.at(-1)?.text !== "Agent finished"
  );
}

function StepText({ text }: Readonly<{ text: string }>) {
  if (text.length <= FOLD_OVER) return <p>{text}</p>;
  return (
    <details>
      <summary>{text.slice(0, 100)}...</summary>
      <pre>{text}</pre>
    </details>
  );
}

export function Steps({
  claimId,
  active,
}: Readonly<{ claimId: string; active: boolean }>) {
  const load = useCallback(() => api.listSteps(claimId), [claimId]);
  const { data: steps } = useLoad(load, (all) => active || running(all));
  if (!steps?.length) return null;
  return (
    <section className="panel" aria-labelledby="steps-title">
      <h3 id="steps-title">What the agent did</h3>
      <ol className="steps">
        {steps.map((step) => (
          <li key={step.id} className={`step ${step.kind}`}>
            <span className="muted">{KINDS[step.kind]}</span>
            <StepText text={step.text} />
          </li>
        ))}
      </ol>
    </section>
  );
}

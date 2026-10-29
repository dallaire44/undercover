import { useCallback } from "react";
import { listSteps, type Step } from "./api";
import { useLoad } from "./useLoad";

const LABELS: Record<Step["kind"], string> = {
  message: "Agent",
  tool_call: "Tool call",
  tool_result: "Tool result",
};
const FOLD_AT = 200;

function StepText({ step }: Readonly<{ step: Step }>) {
  if (step.kind !== "tool_result" || step.text.length <= FOLD_AT)
    return <p className={step.kind === "message" ? "" : "num"}>{step.text}</p>;
  return (
    <details>
      <summary>Result, {step.text.length} characters</summary>
      <pre>{step.text}</pre>
    </details>
  );
}

export function Steps({
  claimId,
  working,
}: Readonly<{ claimId: string; working: boolean }>) {
  const { data: steps } = useLoad(
    useCallback(() => listSteps(claimId), [claimId]),
    () => working,
  );
  if (!steps?.length) return null;
  return (
    <section className="panel" aria-labelledby="steps-title">
      <h2 id="steps-title">What the agent did</h2>
      <ol className="steps">
        {steps.map((step) => (
          <li key={step.id}>
            <span className="muted">{LABELS[step.kind]}</span>
            <StepText step={step} />
          </li>
        ))}
      </ol>
    </section>
  );
}

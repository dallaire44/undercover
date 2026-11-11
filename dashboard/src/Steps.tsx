import { useCallback } from "react";
import { listSteps, type Step } from "./api";
import { SectionsRead } from "./SectionsRead";
import { useLoad } from "./useLoad";

const LABELS: Record<Step["kind"], string> = {
  message: "Agent",
  tool_call: "Tool call",
  tool_result: "Tool result",
  read: "Read",
};
const FOLD_AT = 200;

function StepText({ step }: Readonly<{ step: Step }>) {
  if (step.kind === "read")
    return (
      <details>
        <summary>{step.text.split("\n")[0]}</summary>
        <pre>{step.text}</pre>
      </details>
    );
  if (step.kind !== "tool_result" || step.text.length <= FOLD_AT)
    return <p className={step.kind === "message" ? "" : "num"}>{step.text}</p>;
  return (
    <details>
      <summary>Result, {step.text.length} characters</summary>
      <pre>{step.text}</pre>
    </details>
  );
}

function Timeline({ steps }: Readonly<{ steps: Step[] }>) {
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

export function Steps({
  claimId,
  working,
}: Readonly<{ claimId: string; working: boolean }>) {
  const { data: steps } = useLoad(
    useCallback(() => listSteps(claimId), [claimId]),
    () => working,
  );
  if (!steps) return null;
  return (
    <>
      <SectionsRead steps={steps} />
      {steps.length > 0 && <Timeline steps={steps} />}
    </>
  );
}

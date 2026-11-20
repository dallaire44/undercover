import { useState } from "react";
import {
  getLatestDispatch,
  startDispatch,
  type Run,
  type RunClaim,
  type RunSummary,
} from "./api";
import { AgentsField, FIRST_AGENTS } from "./AgentsField";
import { StatusChip } from "./Chips";
import { duration, modelCost, money } from "./format";
import { useLoad } from "./useLoad";

const agentsAtOnce = (count: number) =>
  `${String(count)} claim agent${count === 1 ? "" : "s"} at once`;

function RunState({ run }: Readonly<{ run: Run }>) {
  if (run.status === "running")
    return <p>Running, {agentsAtOnce(run.agents)}</p>;
  if (run.status === "stopped") return <p>Stopped: {run.reason}</p>;
  return <p>Finished</p>;
}

function RunClaims({ claims }: Readonly<{ claims: RunClaim[] }>) {
  if (!claims.length) return null;
  return (
    <ul className="run-claims" aria-label="Claims in this dispatch">
      {claims.map((claim) => (
        <li key={claim.claim_id}>
          <StatusChip state={claim.status} />
          <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
        </li>
      ))}
    </ul>
  );
}

function Summary({ summary }: Readonly<{ summary: RunSummary }>) {
  const held = summary.awaiting_sign_off.map(
    (claim) => `${claim.claim_id} (${money(claim.payout)})`,
  );
  return (
    <div className="summary" aria-label="Summary">
      <p>
        Approved {summary.approved}, declined {summary.declined}, referred{" "}
        {summary.referred}.
      </p>
      {held.length > 0 && <p>Waiting for sign-off: {held.join(", ")}</p>}
      {summary.needs_handler.length > 0 && (
        <p>Left for a handler: {summary.needs_handler.join(", ")}</p>
      )}
      {summary.in_progress.length > 0 && (
        <p>Still in progress: {summary.in_progress.join(", ")}</p>
      )}
    </div>
  );
}

/** Dispatch the queue with N claim agents at once, and follow the latest dispatch. */
export function RunPanel({
  toWork,
  onStart,
}: Readonly<{ toWork: number; onStart: () => void }>) {
  const [agents, setAgents] = useState(FIRST_AGENTS);
  const [refusal, setRefusal] = useState<string | null>(null);
  const [startedAfter, setStartedAfter] = useState<string | null>();
  const { data: run, reload } = useLoad(
    getLatestDispatch,
    (loaded) =>
      loaded?.status === "running" ||
      (startedAfter !== undefined && (loaded?.run_id ?? null) === startedAfter),
  );
  const running = run?.status === "running";
  const started = (reason: string | null) => {
    setRefusal(reason);
    setStartedAfter(reason ? undefined : (run?.run_id ?? null));
    void reload();
    onStart();
  };
  return (
    <section className="panel run" aria-labelledby="run-title">
      <h2 id="run-title">Dispatch</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void startDispatch(agents).then(started, () => {
            started("The dispatch could not be started.");
          });
        }}
      >
        <AgentsField agents={agents} onChange={setAgents} />
        <button type="submit" disabled={running || toWork === 0}>
          Dispatch the queue
        </button>
      </form>
      {refusal && (
        <p className="refusal" role="alert">
          {refusal}
        </p>
      )}
      {run && (
        <>
          <RunState run={run} />
          <RunClaims claims={run.claims} />
          <p>
            Model cost {modelCost(run.cost)}, time {duration(run.seconds)}
          </p>
          {run.status === "finished" && <Summary summary={run.summary} />}
        </>
      )}
    </section>
  );
}

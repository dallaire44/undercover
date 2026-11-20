import { useCallback } from "react";
import { getEvaluation, type ScoredClaim, type Verdict } from "./api";
import { StatusChip, VerdictChip } from "./Chips";
import {
  duration,
  modelName,
  money,
  percent,
  RUN_STATES,
  setName,
} from "./format";
import { useLoad } from "./useLoad";

const COLUMNS = [
  "Claim",
  "Status",
  "Handler",
  "Agent",
  "Result",
  "Cost of mistake",
  "Model cost",
  "Time",
];
const FIRST_NUMBER = 5;

function Answer({
  decision,
  payout,
}: Readonly<{ decision: Verdict; payout: number }>) {
  return (
    <>
      <VerdictChip verdict={decision} />
      {decision === "approve" && <span className="num"> {money(payout)}</span>}
    </>
  );
}

function Row({ claim }: Readonly<{ claim: ScoredClaim }>) {
  return (
    <tr>
      <td>
        <a href={`#/claims/${claim.claim_id}`}>{claim.copy_of}</a>
      </td>
      <td>
        <StatusChip state={claim.status} />
      </td>
      <td>
        <Answer
          decision={claim.handler_decision}
          payout={claim.handler_payout}
        />
      </td>
      <td>
        <Answer decision={claim.decision} payout={claim.payout} />
      </td>
      <td>
        {claim.right ? "Right" : <span className="chip miss-chip">Miss</span>}
      </td>
      <td className="num right">{money(claim.mistake_cost)}</td>
      <td className="num right">{money(claim.cost)}</td>
      <td className="num right">{duration(claim.seconds)}</td>
    </tr>
  );
}

/** One evaluation: its measures, and each claim beside the handler's decision. */
export function EvaluationPage({ runId }: Readonly<{ runId: string }>) {
  const { data: evaluation, failed } = useLoad(
    useCallback(() => getEvaluation(runId), [runId]),
    (loaded) => loaded?.run.status === "running",
  );
  if (failed) return <p>Evaluation {runId} was not found.</p>;
  if (!evaluation) return <p className="muted">Loading</p>;
  const { run, scores } = evaluation;
  return (
    <>
      <p>
        <a href="#/scoreboard">Back to the scoreboard</a>
      </p>
      <h1>Evaluation {run.run_id}</h1>
      <section className="panel" aria-labelledby="measures-title">
        <h2 id="measures-title">
          {setName(run)}, {run.agents} claim agents at once
        </h2>
        <p>
          {modelName(run)}. {RUN_STATES[run.status]}
          {run.reason ? `: ${run.reason}` : "."}
        </p>
        <dl>
          <dt>Decision accuracy</dt>
          <dd className="num">{percent(scores.decision_accuracy)}</dd>
          <dt>Accuracy</dt>
          <dd className="num">{percent(scores.accuracy)}</dd>
          <dt>Cost of mistakes</dt>
          <dd className="num">{money(scores.cost_of_mistakes)}</dd>
          <dt>Straight through</dt>
          <dd className="num">{percent(scores.straight_through)}</dd>
          <dt>Cost per claim</dt>
          <dd className="num">{money(scores.cost_per_claim)}</dd>
          <dt>Time per claim</dt>
          <dd className="num">{duration(scores.seconds_per_claim)}</dd>
          <dt>Run time</dt>
          <dd className="num">{duration(scores.run_seconds)}</dd>
        </dl>
      </section>
      <section className="panel table-panel" aria-labelledby="claims-title">
        <h2 id="claims-title">Claims</h2>
        <table className="scores">
          <thead>
            <tr>
              {COLUMNS.map((name, index) => (
                <th
                  key={name}
                  scope="col"
                  className={index >= FIRST_NUMBER ? "right" : undefined}
                >
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {evaluation.claims.map((claim) => (
              <Row key={claim.claim_id} claim={claim} />
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

import { useState } from "react";
import {
  listEvaluations,
  startEvaluation,
  type Evaluation,
  type LabelledSet,
} from "./api";
import { AgentsField, FIRST_AGENTS } from "./AgentsField";
import {
  duration,
  modelName,
  money,
  percent,
  RUN_STATES,
  SETS,
  setName,
} from "./format";
import { useLoad } from "./useLoad";

const LABELLED: LabelledSet[] = ["evaluation", "held_out"];
const COLUMNS = [
  "Evaluation",
  "Set",
  "Agents",
  "Model",
  "Status",
  "Decision accuracy",
  "Accuracy",
  "Cost of mistakes",
  "Straight through",
  "Cost per claim",
  "Time per claim",
  "Run time",
];
const FIRST_NUMBER = 5;

function StartEvaluation({
  latest,
  onStart,
}: Readonly<{
  latest: string | null;
  onStart: (after: string | null) => void;
}>) {
  const [claimSet, setClaimSet] = useState<LabelledSet>("evaluation");
  const [tiny, setTiny] = useState(false);
  const [agents, setAgents] = useState(FIRST_AGENTS);
  const [refusal, setRefusal] = useState<string | null>(null);
  const started = (reason: string | null) => {
    setRefusal(reason);
    if (!reason) onStart(latest);
  };
  return (
    <section className="panel start" aria-labelledby="start-title">
      <h2 id="start-title">Start an evaluation</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void startEvaluation(agents, claimSet, tiny).then(started, () => {
            started("The evaluation could not be started.");
          });
        }}
      >
        <label>
          Set{" "}
          <select
            value={claimSet}
            onChange={(event) => {
              setClaimSet(event.target.value as LabelledSet);
            }}
          >
            {LABELLED.map((value) => (
              <option key={value} value={value}>
                {SETS[value]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={tiny}
            onChange={(event) => {
              setTiny(event.target.checked);
            }}
          />{" "}
          Only the five tiny claims
        </label>
        <AgentsField agents={agents} onChange={setAgents} />
        <button type="submit">Start an evaluation</button>
      </form>
      {refusal && (
        <p className="refusal" role="alert">
          {refusal}
        </p>
      )}
    </section>
  );
}

function Row({ evaluation }: Readonly<{ evaluation: Evaluation }>) {
  const { run, scores } = evaluation;
  return (
    <tr>
      <td>
        <a href={`#/scoreboard/${run.run_id}`}>{run.run_id}</a>
      </td>
      <td>{setName(run)}</td>
      <td>{run.agents}</td>
      <td>{modelName(run)}</td>
      <td>{RUN_STATES[run.status]}</td>
      <td className="num right">{percent(scores.decision_accuracy)}</td>
      <td className="num right">{percent(scores.accuracy)}</td>
      <td className="num right">{money(scores.cost_of_mistakes)}</td>
      <td className="num right">{percent(scores.straight_through)}</td>
      <td className="num right">{money(scores.cost_per_claim)}</td>
      <td className="num right">{duration(scores.seconds_per_claim)}</td>
      <td className="num right">{duration(scores.run_seconds)}</td>
    </tr>
  );
}

/** Start evaluations, and list them newest first with their measures. */
export function Scoreboard() {
  const [startedAfter, setStartedAfter] = useState<string | null>();
  const latest = (found?: Evaluation[]) => found?.[0]?.run.run_id ?? null;
  const { data: evaluations, failed } = useLoad(
    listEvaluations,
    (loaded) =>
      (loaded ?? []).some((e) => e.run.status === "running") ||
      (startedAfter !== undefined && latest(loaded) === startedAfter),
  );
  return (
    <>
      <h1>Scoreboard</h1>
      <StartEvaluation latest={latest(evaluations)} onStart={setStartedAfter} />
      <section
        className="panel table-panel"
        aria-labelledby="evaluations-title"
      >
        <h2 id="evaluations-title">Evaluations</h2>
        {failed && <p>The evaluations could not be loaded.</p>}
        {evaluations?.length === 0 && <p className="muted">None yet.</p>}
        {evaluations && evaluations.length > 0 && (
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
              {evaluations.map((evaluation) => (
                <Row key={evaluation.run.run_id} evaluation={evaluation} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}

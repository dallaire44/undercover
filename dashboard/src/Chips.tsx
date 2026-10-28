import type { State, Verdict } from "./api";
import { STATES, VERDICTS } from "./states";

export function StatusChip({ status }: Readonly<{ status: State }>) {
  const label = STATES.find((state) => state.key === status)?.label;
  return <span className={`chip state-${status}`}>{label}</span>;
}

export function VerdictChip({ verdict }: Readonly<{ verdict: Verdict }>) {
  const { label, like } = VERDICTS[verdict];
  return <span className={`chip state-${like}`}>{label}</span>;
}

import type { State, Verdict } from "./api";
import { STATES, VERDICTS } from "./format";

export function StatusChip({ state }: Readonly<{ state: State }>) {
  return <span className={`chip state-${state}`}>{STATES[state]}</span>;
}

export function VerdictChip({ verdict }: Readonly<{ verdict: Verdict }>) {
  return <span className={`chip verdict-${verdict}`}>{VERDICTS[verdict]}</span>;
}

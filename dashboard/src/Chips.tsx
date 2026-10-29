import type { State, Verdict } from "./api";
import { STATES, VERDICTS } from "./format";

const SYMBOLS: Record<Verdict, string> = {
  approve: "M2 7.5l3.5 3.5L12 3.5",
  decline: "M3 3l8 8M11 3l-8 8",
  refer: "M2 7h9M7.5 3l4 4-4 4",
};

export function StatusChip({ state }: Readonly<{ state: State }>) {
  return <span className={`chip state-${state}`}>{STATES[state]}</span>;
}

/** The symbol shows only in color-blind mode, which the stylesheet decides. */
export function VerdictChip({ verdict }: Readonly<{ verdict: Verdict }>) {
  return (
    <span className={`chip verdict-${verdict}`}>
      <svg
        className="verdict-symbol"
        viewBox="0 0 14 14"
        aria-hidden="true"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={SYMBOLS[verdict]} />
      </svg>
      {VERDICTS[verdict]}
    </span>
  );
}

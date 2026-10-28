import type { State, Verdict } from "./api";
import { STATES, VERDICTS } from "./states";

export function StatusChip({ status }: Readonly<{ status: State }>) {
  const label = STATES.find((state) => state.key === status)?.label;
  return <span className={`chip state-${status}`}>{label}</span>;
}

const SYMBOLS: Record<Verdict, string> = {
  approve: "M2 7.5l3.2 3.2L12 3.5",
  decline: "M3 3l8 8M11 3l-8 8",
  refer: "M2 7h9M7.5 3.2L11.3 7l-3.8 3.8",
};

/** The symbol shows only in color-blind mode, and the word says it for screen readers. */
export function VerdictChip({ verdict }: Readonly<{ verdict: Verdict }>) {
  const { label, like } = VERDICTS[verdict];
  return (
    <span className={`chip state-${like}`}>
      <svg
        className="symbol"
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
      {label}
    </span>
  );
}

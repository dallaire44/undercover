import type { State, Verdict } from "./api";

export const STATES: readonly { key: State; label: string }[] = [
  { key: "waiting", label: "Waiting" },
  { key: "in_progress", label: "In progress" },
  { key: "awaiting_sign_off", label: "Waiting for sign-off" },
  { key: "decided", label: "Decided" },
];

/** A decision takes the color of the claim state it matches. */
export const VERDICTS: Record<Verdict, { label: string; like: State }> = {
  approve: { label: "Approved", like: "decided" },
  decline: { label: "Declined", like: "in_progress" },
  refer: { label: "Referred", like: "awaiting_sign_off" },
};

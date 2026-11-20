import type { Run, State, Verdict } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export const money = (amount: number) => dollars.format(amount);

const fractions = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 4,
});

/** A model cost, to a hundredth of a cent, since a claim costs a fraction of one. */
export const modelCost = (amount: number) => fractions.format(amount);

export const percent = (share: number) => `${String(Math.round(share * 100))}%`;

/** A time in whole seconds, such as "45 s" or "1 min 12 s". */
export function duration(seconds: number) {
  const whole = Math.round(seconds);
  const minutes = Math.floor(whole / 60);
  const rest = `${String(whole % 60)} s`;
  return minutes ? `${String(minutes)} min ${rest}` : rest;
}

export const date = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "UTC",
  }) + " UTC";

export const STATES: Record<State, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  awaiting_sign_off: "Waiting for sign-off",
  decided: "Decided",
  needs_handler: "Needs a handler",
};

export const VERDICTS: Record<Verdict, string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred",
};

export const titleCase = (snake: string) =>
  snake.charAt(0).toUpperCase() + snake.slice(1).replaceAll("_", " ");

export const SETS: Record<Run["claim_set"], string> = {
  queue: "The queue",
  evaluation: "Evaluation set",
  held_out: "Held-out set",
};

export const RUN_STATES: Record<Run["status"], string> = {
  running: "Running",
  finished: "Finished",
  stopped: "Stopped",
};

export const setName = (run: Run) =>
  `${SETS[run.claim_set]}${run.tiny ? ", tiny" : ""}`;

export const modelName = (run: Run) =>
  `${run.model}, ${run.reasoning_effort} effort`;

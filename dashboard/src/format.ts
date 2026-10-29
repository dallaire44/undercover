import type { State, Verdict } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export const money = (amount: number) => dollars.format(amount);

export const date = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });

export const STATES: Record<State, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  awaiting_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const VERDICTS: Record<Verdict, string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred",
};

export const titleCase = (snake: string) =>
  snake.charAt(0).toUpperCase() + snake.slice(1).replaceAll("_", " ");

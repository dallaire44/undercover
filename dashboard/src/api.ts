export type State =
  "waiting" | "in_progress" | "awaiting_sign_off" | "decided" | "needs_handler";
export type Verdict = "approve" | "decline" | "refer";

export interface ClaimSummary {
  claim_id: string;
  summary: string;
  claim_type: string;
  amount_claimed: number;
  submitted_on: string;
  customer_name: string;
  status: State;
  attempts: number;
  run_id: string | null;
  thread_id: string | null;
  copy_of: string | null;
  decision: Verdict | null;
  payout: number | null;
}

export interface ClaimItem {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: Verdict;
  payout: number;
  reason: string;
  policy_section: string;
  decided_at: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
  signed_off_by: string | null;
  signed_off_at: string | null;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_at: string;
}

export interface RunClaim extends ClaimSummary {
  cost: number;
  seconds: number;
}

export interface RunSummary {
  approved: number;
  declined: number;
  referred: number;
  awaiting_sign_off: { claim_id: string; payout: number }[];
  needs_handler: string[];
  in_progress: string[];
}

export interface Run {
  run_id: string;
  kind: "dispatch" | "evaluation";
  agents: number;
  claim_set: "queue" | "evaluation" | "held_out";
  tiny: boolean;
  model: string;
  reasoning_effort: string;
  status: "running" | "finished" | "stopped";
  reason: string | null;
  started_at: string;
  finished_at: string | null;
  claims: RunClaim[];
  summary: RunSummary;
  cost: number;
  seconds: number;
}

export type LabelledSet = "evaluation" | "held_out";

export interface ScoredClaim {
  claim_id: string;
  copy_of: string;
  status: State;
  decision: Verdict;
  payout: number;
  handler_decision: Verdict;
  handler_payout: number;
  decision_right: boolean;
  right: boolean;
  mistake_cost: number;
  cost: number;
  seconds: number;
}

export interface Scores {
  decision_accuracy: number;
  accuracy: number;
  cost_of_mistakes: number;
  straight_through: number;
  cost_per_claim: number;
  seconds_per_claim: number;
  run_seconds: number;
}

export interface Evaluation {
  run: Run;
  scores: Scores;
  claims: ScoredClaim[];
}

export interface ClaimDetail {
  claim_id: string;
  summary: string;
  claim_type: string;
  amount_claimed: number;
  submitted_on: string;
  customer_name: string;
  status: State;
  attempts: number;
  run_id: string | null;
  thread_id: string | null;
  copy_of: string | null;
  policy_id: string;
  customer_id: string;
  incident_date: string;
  incident_location: string;
  story: string;
  items: ClaimItem[];
  documents: ClaimDocument[];
  decision: Decision | null;
  payment: Payment | null;
  sign_off: SignOff | null;
}

export interface Step {
  id: number;
  claim_id: string;
  thread_id: string;
  kind: "message" | "tool_call" | "tool_result" | "read";
  text: string;
  created_at: string;
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

export interface Policy {
  policy_id: string;
  plan_name: string;
  add_ons: string[];
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface History {
  name: string;
  previous_claims: PreviousClaim[];
}

async function request(path: string, init?: RequestInit) {
  const response = await fetch(path, init);
  if (!response.ok)
    throw new Error(`${path} returned ${String(response.status)}`);
  return response;
}

async function get<T>(path: string): Promise<T> {
  return (await (await request(path)).json()) as T;
}

const posting = (body?: object): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

const post = (path: string, body?: object) => request(path, posting(body));

/** Ask the backend to start some work. Resolve with its reason if it refuses. */
async function start(path: string, body?: object): Promise<string | null> {
  const response = await fetch(path, posting(body));
  if (response.status === 409)
    return ((await response.json()) as { detail: string }).detail;
  if (!response.ok)
    throw new Error(`${path} returned ${String(response.status)}`);
  return null;
}

export const listClaims = () => get<ClaimSummary[]>("/api/claims");
export const getClaim = (id: string) => get<ClaimDetail>(`/api/claims/${id}`);
export const getPolicy = (id: string) => get<Policy>(`/api/policies/${id}`);
export const getHistory = (customerId: string) =>
  get<History>(`/api/customers/${customerId}/history`);
export const listSteps = (id: string) => get<Step[]>(`/api/claims/${id}/steps`);
export const listHandlers = () => get<Handler[]>("/api/handlers");
export const getInstructions = async () =>
  (await request("/api/instructions/claim")).text();
export const startAgent = (id: string) => start(`/api/claims/${id}/agent`);
export const startDispatch = (agents: number) =>
  start("/api/dispatches/start", { agents });
export const getLatestDispatch = () =>
  get<Run | null>("/api/dispatches/latest");
export const signOff = (id: string, handlerId: string) =>
  post(`/api/claims/${id}/sign-off`, { handler_id: handlerId });
export const startEvaluation = (
  agents: number,
  claimSet: LabelledSet,
  tiny: boolean,
) => start("/api/evaluations/start", { agents, claim_set: claimSet, tiny });
export const listEvaluations = () => get<Evaluation[]>("/api/evaluations");
export const getEvaluation = (runId: string) =>
  get<Evaluation>(`/api/evaluations/${runId}`);

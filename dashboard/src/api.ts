export type State = "waiting" | "in_progress" | "awaiting_sign_off" | "decided";
export type Verdict = "approve" | "decline" | "refer";

export interface ClaimSummary {
  claim_id: string;
  summary: string;
  claim_type: string;
  amount_claimed: number;
  submitted_on: string;
  customer_name: string;
  status: State;
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
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_at: string;
}

export interface ClaimDetail {
  claim_id: string;
  summary: string;
  claim_type: string;
  amount_claimed: number;
  submitted_on: string;
  customer_name: string;
  status: State;
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
  kind: "message" | "tool_call" | "tool_result";
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

const post = (path: string, body?: object) =>
  request(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });

export const listClaims = () => get<ClaimSummary[]>("/api/claims");
export const getClaim = (id: string) => get<ClaimDetail>(`/api/claims/${id}`);
export const getPolicy = (id: string) => get<Policy>(`/api/policies/${id}`);
export const getHistory = (customerId: string) =>
  get<History>(`/api/customers/${customerId}/history`);
export const listSteps = (id: string) => get<Step[]>(`/api/claims/${id}/steps`);
export const listHandlers = () => get<Handler[]>("/api/handlers");
export const getInstructions = async () =>
  (await request("/api/instructions")).text();
export const startAgent = (id: string) => post(`/api/claims/${id}/agent`);
export const workQueue = () => post("/api/queue/agent");
export const signOff = (id: string, handlerId: string) =>
  post(`/api/claims/${id}/sign-off`, { handler_id: handlerId });

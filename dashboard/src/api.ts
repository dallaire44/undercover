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

export interface Item {
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

export interface Claim {
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
  items: Item[];
  documents: ClaimDocument[];
  decision: Decision | null;
  payment: Payment | null;
  sign_off: SignOff | null;
}

export interface Policy {
  policy_id: string;
  plan: string;
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

export interface ClaimHistory {
  name: string;
  previous_claims: PreviousClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

export interface Step {
  id: number;
  thread_id: string;
  kind: "message" | "tool_call" | "tool_result";
  text: string;
  created_at: string;
}

async function send<T>(
  path: string,
  method: string,
  body?: object,
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const problem = (await response.json()) as { detail?: string };
    throw new Error(
      problem.detail ?? `${path} answered ${String(response.status)}`,
    );
  }
  return (await response.json()) as T;
}

const get = <T>(path: string) => send<T>(path, "GET");

export const api = {
  listClaims: () => get<ClaimSummary[]>("/api/claims"),
  getClaim: (id: string) => get<Claim>(`/api/claims/${id}`),
  getPolicy: (id: string) => get<Policy>(`/api/policies/${id}`),
  getClaimHistory: (id: string) =>
    get<ClaimHistory>(`/api/customers/${id}/history`),
  listHandlers: () => get<Handler[]>("/api/handlers"),
  listSteps: (id: string) => get<Step[]>(`/api/claims/${id}/steps`),
  getInstructions: () => get<{ text: string }>("/api/instructions"),
  startAgent: (id: string) => send<Claim>(`/api/claims/${id}/agent`, "POST"),
  workQueue: () => send<string[]>("/api/queue/agent", "POST"),
  signOff: (id: string, handlerId: string) =>
    send<Claim>(`/api/claims/${id}/sign-off`, "POST", {
      handler_id: handlerId,
    }),
};

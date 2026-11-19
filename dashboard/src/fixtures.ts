import { vi } from "vitest";
import type {
  ClaimDetail,
  ClaimSummary,
  Handler,
  History,
  Policy,
  Run,
  Step,
} from "./api";

export const waitingClaim: ClaimSummary = {
  claim_id: "CLM-1001",
  summary: "Flight home canceled by the airline",
  claim_type: "trip_delay",
  amount_claimed: 420,
  submitted_on: "2026-06-24",
  customer_name: "Maya Patel",
  status: "waiting",
  attempts: 0,
  run_id: null,
  thread_id: null,
  decision: null,
  payout: null,
};

export const decidedClaim: ClaimSummary = {
  ...waitingClaim,
  claim_id: "CLM-1014",
  customer_name: "Sam Lee",
  amount_claimed: 700,
  status: "decided",
  decision: "approve",
  payout: 650,
};

export const declinedClaim: ClaimSummary = {
  ...decidedClaim,
  claim_id: "CLM-1015",
  decision: "decline",
  payout: 0,
};

export const detail: ClaimDetail = {
  ...waitingClaim,
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  story: "My flight home from Rome was canceled.",
  items: [
    { description: "Airport hotel", category: "accommodation", amount: 245 },
  ],
  documents: [
    { name: "Hotel receipt", type: "receipt", content: "Hotel Aurelia." },
  ],
  decision: null,
  payment: null,
  sign_off: null,
};

export const decidedDetail: ClaimDetail = {
  ...detail,
  status: "decided",
  decision: {
    decision: "approve",
    payout: 420,
    reason: "The wording covers it.",
    policy_section: "3. Trip Delay",
    decided_at: "2026-06-25T10:00:00+00:00",
  },
  payment: {
    amount: 420,
    paid_at: "2026-06-25T10:02:01+00:00",
    signed_off_by: "Dana Whitfield",
    signed_off_at: "2026-06-25T10:00:00+00:00",
  },
  sign_off: {
    handler_id: "HND-01",
    handler_name: "Dana Whitfield",
    signed_at: "2026-06-25T10:00:00+00:00",
  },
};

export const policy: Policy = {
  policy_id: "POL-2001",
  plan_name: "Premium",
  add_ons: [],
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3200,
  },
  travelers: ["Maya Patel"],
};

export const history: History = {
  name: "Maya Patel",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2025-03-02",
      claim_type: "baggage_delay",
      summary: "Bag arrived late",
      outcome: "approved",
      amount_paid: 150,
    },
  ],
};

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
  },
  { handler_id: "HND-03", name: "Priya Raman", role: "Claims Handler" },
];

export function step(id: number, kind: Step["kind"], text: string): Step {
  return {
    id,
    claim_id: "CLM-1001",
    thread_id: "t1",
    kind,
    text,
    created_at: "2026-06-25T10:00:00+00:00",
  };
}

/** Answer each fetch with what is registered for its path. Strings go as text. */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string) => {
    if (!(path in routes))
      return Promise.resolve(new Response("", { status: 404 }));
    const body = routes[path];
    return Promise.resolve(
      new Response(typeof body === "string" ? body : JSON.stringify(body)),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export const runningRun: Run = {
  run_id: "RUN-0001",
  cap: 5,
  status: "running",
  summary: "",
  started_at: "2026-06-25T10:00:00+00:00",
  finished_at: null,
  claim_ids: ["CLM-1001"],
  todos: [
    { content: "CLM-1001: trip delay, $420.00", status: "done" },
    { content: "CLM-1004: baggage delay, $186.00", status: "in_progress" },
    { content: "CLM-1009: baggage, $980.00", status: "left_for_handler" },
    { content: "Check for missed claims", status: "to_do" },
  ],
};

export const finishedRun: Run = {
  ...runningRun,
  status: "finished",
  summary: "Worked 3 claims. Total paid: $420.00.",
  finished_at: "2026-06-25T10:05:00+00:00",
  claim_ids: ["CLM-1001", "CLM-1004", "CLM-1009"],
};

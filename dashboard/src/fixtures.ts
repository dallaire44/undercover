import type {
  Claim,
  ClaimHistory,
  ClaimSummary,
  Handler,
  Policy,
  Step,
} from "./api";

export const queue: ClaimSummary[] = [
  {
    claim_id: "CLM-1001",
    summary: "Flight home canceled by the airline",
    claim_type: "trip_delay",
    amount_claimed: 420,
    submitted_on: "2026-06-24",
    customer_name: "Maya Patel",
    status: "waiting",
    decision: null,
    payout: null,
  },
  {
    claim_id: "CLM-1002",
    summary: "Checked bag lost on the way out",
    claim_type: "baggage",
    amount_claimed: 1250,
    submitted_on: "2026-06-25",
    customer_name: "Tom Reyes",
    status: "decided",
    decision: "approve",
    payout: 580,
  },
  {
    claim_id: "CLM-1004",
    summary: "Skydiving injury",
    claim_type: "emergency_medical",
    amount_claimed: 9000,
    submitted_on: "2026-06-26",
    customer_name: "Lena Fox",
    status: "decided",
    decision: "decline",
    payout: 0,
  },
];

export const claim: Claim = {
  claim_id: "CLM-1001",
  summary: "Flight home canceled by the airline",
  claim_type: "trip_delay",
  amount_claimed: 420,
  submitted_on: "2026-06-24",
  customer_name: "Maya Patel",
  status: "waiting",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  story: "My flight home from Rome was canceled.",
  items: [
    {
      description: "Airport hotel, one night",
      category: "accommodation",
      amount: 245,
    },
    { description: "Dinner and breakfast", category: "meals", amount: 95 },
  ],
  documents: [
    {
      name: "Hotel receipt",
      type: "receipt",
      content: "Hotel Aurelia. One night.",
    },
  ],
  decision: null,
  payment: null,
  sign_off: null,
};

export const decidedClaim: Claim = {
  ...claim,
  status: "awaiting_sign_off",
  decision: {
    decision: "approve",
    payout: 3750,
    reason: "The costs are covered delay costs.",
    policy_section: "Section 3, Trip Delay",
    decided_at: "2026-10-28T21:29:40+00:00",
  },
};

export const policy: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  add_ons: [],
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

export const history: ClaimHistory = {
  name: "Maya Patel",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2024-08-19",
      claim_type: "baggage_delay",
      summary: "Checked bag arrived 30 hours late in Lisbon",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
  },
  { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Claims Handler" },
  { handler_id: "HND-03", name: "Priya Raman", role: "Claims Handler" },
];

export const longResult = "x".repeat(300);

export const steps: Step[] = [
  {
    id: 1,
    thread_id: "t1",
    kind: "message",
    text: "Agent started",
    created_at: "2026-10-28T10:00:00+00:00",
  },
  {
    id: 2,
    thread_id: "t1",
    kind: "tool_call",
    text: 'get_claim({"claim_id": "CLM-1001"})',
    created_at: "2026-10-28T10:00:01+00:00",
  },
  {
    id: 3,
    thread_id: "t1",
    kind: "tool_result",
    text: longResult,
    created_at: "2026-10-28T10:00:02+00:00",
  },
  {
    id: 4,
    thread_id: "t1",
    kind: "message",
    text: "Agent finished",
    created_at: "2026-10-28T10:00:03+00:00",
  },
];

/**
 * Answer fetch calls by URL. A key is a URL for a GET, or "POST /url". A value
 * is the body, or a function that gets the request and returns the body or a Response.
 */
export function stubFetch(routes: Record<string, unknown>): typeof fetch {
  return (input, init) => {
    const url = input instanceof Request ? input.url : input.toString();
    const key =
      init?.method && init.method !== "GET" ? `${init.method} ${url}` : url;
    const route = routes[key];
    if (route === undefined)
      return Promise.resolve(new Response("{}", { status: 404 }));
    const body =
      typeof route === "function"
        ? (route as (i?: RequestInit) => unknown)(init)
        : route;
    return Promise.resolve(
      body instanceof Response ? body : new Response(JSON.stringify(body)),
    );
  };
}

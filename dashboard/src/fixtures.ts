import type { Claim, ClaimHistory, ClaimSummary, Policy } from "./api";

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

/** Answer fetch calls with these bodies, by URL. */
export function stubFetch(routes: Record<string, unknown>): typeof fetch {
  return (input) => {
    const url = input instanceof Request ? input.url : input.toString();
    const body = routes[url];
    return Promise.resolve(
      body === undefined
        ? new Response("{}", { status: 404 })
        : new Response(JSON.stringify(body)),
    );
  };
}

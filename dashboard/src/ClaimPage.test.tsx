import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClaimPage } from "./ClaimPage";
import { claim, decidedClaim, history, policy, stubFetch } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const related = {
  "/api/policies/POL-2001": policy,
  "/api/customers/CUS-3001/history": history,
};

it("shows a claim without a decision", async () => {
  vi.stubGlobal(
    "fetch",
    stubFetch({ "/api/claims/CLM-1001": claim, ...related }),
  );
  render(<ClaimPage id="CLM-1001" />);
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("$245.00")).toBeDefined();
  expect(screen.getByText("Hotel receipt")).toBeDefined();
  expect(screen.queryByText("The agent's decision")).toBeNull();
  expect(screen.queryByText(/Payment on hold/)).toBeNull();
});

it("shows the policy and the earlier claims", async () => {
  vi.stubGlobal(
    "fetch",
    stubFetch({ "/api/claims/CLM-1001": claim, ...related }),
  );
  render(<ClaimPage id="CLM-1001" />);
  expect(await screen.findByText("Rome, Italy")).toBeDefined();
  expect(screen.getByText("Premium")).toBeDefined();
  expect(screen.getByText("$3,100.00")).toBeDefined();
  expect(screen.getByText("None")).toBeDefined();
  expect(await screen.findByText(/CLM-0412/)).toBeDefined();
});

it("shows the decision, the reason and the hold on a payout over the limit", async () => {
  vi.stubGlobal(
    "fetch",
    stubFetch({ "/api/claims/CLM-1001": decidedClaim, ...related }),
  );
  render(<ClaimPage id="CLM-1001" />);
  expect(await screen.findByText("The agent's decision")).toBeDefined();
  expect(screen.getByText("Approved")).toBeDefined();
  expect(screen.getByText("$3,750.00")).toBeDefined();
  expect(screen.getByText("The costs are covered delay costs.")).toBeDefined();
  expect(screen.getByText("Section 3, Trip Delay")).toBeDefined();
  expect(screen.getByText(/Payment on hold/)).toBeDefined();
});

it("shows the payment and the sign-off once they exist", async () => {
  const paid = {
    ...decidedClaim,
    status: "decided",
    payment: { amount: 3750, paid_at: "2026-10-29T10:00:00+00:00" },
    sign_off: {
      handler_id: "HND-01",
      handler_name: "Dana Whitfield",
      signed_at: "2026-10-29T10:00:00+00:00",
    },
  };
  vi.stubGlobal(
    "fetch",
    stubFetch({ "/api/claims/CLM-1001": paid, ...related }),
  );
  render(<ClaimPage id="CLM-1001" />);
  expect(await screen.findByText(/Paid \$3,750.00/)).toBeDefined();
  expect(screen.getByText(/Signed off by Dana Whitfield/)).toBeDefined();
  expect(screen.queryByText(/Payment on hold/)).toBeNull();
});

it("says when the claim could not be loaded", async () => {
  vi.stubGlobal("fetch", stubFetch({}));
  render(<ClaimPage id="CLM-9999" />);
  expect((await screen.findByRole("alert")).textContent).toContain("CLM-9999");
});

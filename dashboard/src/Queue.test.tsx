import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { decidedClaim, declinedClaim, stubApi, waitingClaim } from "./fixtures";
import { Queue } from "./Queue";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const claims = [waitingClaim, decidedClaim, declinedClaim];

it("shows the eight columns in order", () => {
  render(<Queue claims={claims} onWork={vi.fn()} />);
  const headers = screen
    .getAllByRole("columnheader")
    .map((header) => header.textContent);
  expect(headers).toEqual([
    "Claim",
    "Customer",
    "Type",
    "Submitted",
    "Claimed",
    "Status",
    "Decision",
    "Payout",
  ]);
});

it("shows a claim with its customer, summary and link", () => {
  render(<Queue claims={claims} onWork={vi.fn()} />);
  const row = screen.getByRole("row", { name: /CLM-1001/ });
  expect(within(row).getByRole("link").getAttribute("href")).toBe(
    "#/claims/CLM-1001",
  );
  expect(within(row).getByText("Maya Patel")).toBeDefined();
  expect(
    within(row).getByText("Flight home canceled by the airline"),
  ).toBeDefined();
  expect(within(row).getByText("Trip delay")).toBeDefined();
  expect(within(row).getByText("$420.00")).toBeDefined();
});

it("shows a decided row with its decision and payout", () => {
  render(<Queue claims={claims} onWork={vi.fn()} />);
  const row = screen.getByRole("row", { name: /CLM-1014/ });
  expect(within(row).getByText("Approved")).toBeDefined();
  expect(within(row).getByText("$650.00")).toBeDefined();
});

it("shows a declined row with a payout of zero", () => {
  render(<Queue claims={claims} onWork={vi.fn()} />);
  const row = screen.getByRole("row", { name: /CLM-1015/ });
  expect(within(row).getByText("Declined")).toBeDefined();
  expect(within(row).getByText("$0.00")).toBeDefined();
});

it("shows a dash for the decision and payout of an undecided row", () => {
  render(<Queue claims={claims} onWork={vi.fn()} />);
  const row = screen.getByRole("row", { name: /CLM-1001/ });
  expect(within(row).getAllByText("—")).toHaveLength(2);
});

it("counts the claims in each state", () => {
  render(<Queue claims={claims} onWork={vi.fn()} />);
  const counts = within(screen.getByRole("list", { name: "Claims by status" }));
  const count = (label: string) =>
    counts.getByText(label).closest("li")?.querySelector("strong")?.textContent;
  expect(count("Waiting")).toBe("1");
  expect(count("In progress")).toBe("0");
  expect(count("Waiting for sign-off")).toBe("0");
  expect(count("Decided")).toBe("2");
  expect(count("Needs a handler")).toBe("0");
});

it("counts the claims left for a handler", () => {
  const left = {
    ...waitingClaim,
    claim_id: "CLM-1009",
    status: "needs_handler" as const,
  };
  render(<Queue claims={[left, ...claims]} onWork={vi.fn()} />);
  const counts = within(screen.getByRole("list", { name: "Claims by status" }));
  const tile = counts.getByText("Needs a handler").closest("li");
  expect(tile?.querySelector("strong")?.textContent).toBe("1");
  const row = screen.getByRole("row", { name: /CLM-1009/ });
  expect(within(row).getByText("Needs a handler").className).toBe(
    "chip state-needs_handler",
  );
  expect(within(row).getAllByText("—")).toHaveLength(2);
});

it("offers a dispatch while a claim is waiting or in progress", () => {
  stubApi({});
  const dispatch = () =>
    screen.getByRole("button", { name: "Dispatch the queue" });
  const settled = claims.filter((claim) => claim.status === "decided");
  render(<Queue claims={claims} onWork={vi.fn()} />);
  expect(dispatch().hasAttribute("disabled")).toBe(false);
  cleanup();
  render(<Queue claims={settled} onWork={vi.fn()} />);
  expect(dispatch().hasAttribute("disabled")).toBe(true);
});

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
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
});

it("works the queue and then asks for a refresh", async () => {
  const fetchMock = stubApi({ "/api/queue/agent": [] });
  const onWork = vi.fn();
  render(<Queue claims={claims} onWork={onWork} />);
  fireEvent.click(screen.getByRole("button", { name: "Work the queue" }));
  await waitFor(() => {
    expect(onWork).toHaveBeenCalled();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/queue/agent",
    expect.objectContaining({ method: "POST" }),
  );
});

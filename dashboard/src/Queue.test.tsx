import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { queue, stubFetch } from "./fixtures";
import { Queue } from "./Queue";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function showQueue() {
  vi.stubGlobal("fetch", stubFetch({ "/api/claims": queue }));
  render(<Queue />);
}

function count(label: string): string {
  const item = screen
    .getAllByRole("listitem")
    .find((li) => li.textContent.endsWith(label));
  if (!item) throw new Error(`No count for ${label}`);
  return within(item).getByText(/^\d+$/).textContent;
}

it("counts the claims in each state", async () => {
  showQueue();
  await screen.findByText("CLM-1001");
  expect(count("Waiting")).toBe("1");
  expect(count("In progress")).toBe("0");
  expect(count("Waiting for sign-off")).toBe("0");
  expect(count("Decided")).toBe("2");
});

it("shows a row for each claim with the eight columns", async () => {
  showQueue();
  await screen.findByText("CLM-1001");
  const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
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
  const row = screen.getByRole("row", { name: /CLM-1001/ });
  expect(within(row).getByRole("link").getAttribute("href")).toBe(
    "#/claims/CLM-1001",
  );
  expect(row.textContent).toContain("Maya Patel");
  expect(row.textContent).toContain("Flight home canceled by the airline");
  expect(row.textContent).toContain("Trip delay");
  expect(row.textContent).toContain("Jun 24, 2026");
  expect(row.textContent).toContain("$420.00");
});

it("shows the decision and payout of a decided claim", async () => {
  showQueue();
  await screen.findByText("CLM-1002");
  const approved = screen.getByRole("row", { name: /CLM-1002/ });
  expect(within(approved).getByText("Approved")).toBeDefined();
  expect(within(approved).getByText("$580.00")).toBeDefined();
  const declined = screen.getByRole("row", { name: /CLM-1004/ });
  expect(within(declined).getByText("Declined")).toBeDefined();
  expect(within(declined).getByText("$0.00")).toBeDefined();
});

it("shows a dash in both columns before the agent has decided", async () => {
  showQueue();
  await screen.findByText("CLM-1001");
  const row = screen.getByRole("row", { name: /CLM-1001/ });
  expect(within(row).getAllByText("–")).toHaveLength(2);
});

it("says when the queue could not be loaded", async () => {
  vi.stubGlobal("fetch", stubFetch({}));
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "could not be loaded",
  );
});

it("works the queue when asked", async () => {
  const work = vi.fn(() => ["CLM-1001"]);
  vi.stubGlobal(
    "fetch",
    stubFetch({ "/api/claims": queue, "POST /api/queue/agent": work }),
  );
  render(<Queue />);
  await screen.findByText("CLM-1001");
  fireEvent.click(screen.getByRole("button", { name: "Work the queue" }));
  await vi.waitFor(() => {
    expect(work).toHaveBeenCalledOnce();
  });
});

it("refreshes every two seconds", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  let calls = 0;
  const growing = () => {
    calls += 1;
    return calls < 2 ? queue : queue.map((c) => ({ ...c, status: "decided" }));
  };
  vi.stubGlobal("fetch", stubFetch({ "/api/claims": growing }));
  render(<Queue />);
  await screen.findByText("CLM-1001");
  expect(count("Decided")).toBe("2");
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(count("Decided")).toBe("3");
});

import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { longResult, stubFetch, steps } from "./fixtures";
import { Steps } from "./Steps";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("lists the steps in order, with what each one is", async () => {
  vi.stubGlobal("fetch", stubFetch({ "/api/claims/CLM-1001/steps": steps }));
  render(<Steps claimId="CLM-1001" active={false} />);
  await screen.findByText('get_claim({"claim_id": "CLM-1001"})');
  const items = screen.getAllByRole("listitem");
  expect(items).toHaveLength(4);
  expect(items[0]?.textContent).toBe("The agent saysAgent started");
  expect(items[1]?.textContent).toContain("Tool call");
  expect(items[2]?.textContent).toContain("Tool result");
});

it("folds away a long tool result", async () => {
  vi.stubGlobal("fetch", stubFetch({ "/api/claims/CLM-1001/steps": steps }));
  render(<Steps claimId="CLM-1001" active={false} />);
  const summary = await screen.findByText(/^x{100}\.\.\.$/);
  expect(summary.tagName).toBe("SUMMARY");
  expect(screen.getByText(longResult).tagName).toBe("PRE");
});

it("shows nothing when the agent has not worked on the claim", async () => {
  const fetchSteps = vi.fn(stubFetch({ "/api/claims/CLM-1002/steps": [] }));
  vi.stubGlobal("fetch", fetchSteps);
  render(<Steps claimId="CLM-1002" active={false} />);
  await vi.waitFor(() => {
    expect(fetchSteps).toHaveBeenCalled();
  });
  expect(screen.queryByRole("heading")).toBeNull();
});

it("polls every two seconds while the claim is in progress", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  let calls = 0;
  const growing = () => steps.slice(0, Math.min(++calls, steps.length));
  vi.stubGlobal("fetch", stubFetch({ "/api/claims/CLM-1001/steps": growing }));
  render(<Steps claimId="CLM-1001" active />);
  await screen.findByText("Agent started");
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
  await act(() => vi.advanceTimersByTimeAsync(4000));
  expect(screen.getAllByRole("listitem")).toHaveLength(4);
});

it("keeps polling after the claim leaves in progress, until the run has finished", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  let calls = 0;
  const unfinished = () => (++calls < 2 ? steps.slice(0, 2) : steps);
  vi.stubGlobal(
    "fetch",
    stubFetch({ "/api/claims/CLM-1001/steps": unfinished }),
  );
  render(<Steps claimId="CLM-1001" active={false} />);
  await screen.findByText("Agent started");
  expect(screen.queryByText("Agent finished")).toBeNull();
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(screen.getByText("Agent finished")).toBeDefined();
});

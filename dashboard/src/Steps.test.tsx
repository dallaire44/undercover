import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { step, stubApi } from "./fixtures";
import { Steps } from "./Steps";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const long = "x".repeat(300);
const steps = [
  step(1, "message", "Agent started"),
  step(2, "tool_call", 'get_claim({"claim_id": "CLM-1001"})'),
  step(3, "tool_result", "short result"),
  step(4, "tool_result", long),
];

it("lists the steps in order and folds long results", async () => {
  stubApi({ "/api/claims/CLM-1001/steps": steps });
  render(<Steps claimId="CLM-1001" working={false} />);
  expect(await screen.findByText("Agent started")).toBeDefined();
  const items = screen.getAllByRole("listitem").map((item) => item.textContent);
  expect(items[0]).toContain("Agent started");
  expect(items[1]).toContain("get_claim");
  expect(items[2]).toContain("short result");
  expect(screen.getByText("Result, 300 characters")).toBeDefined();
  expect(screen.getByText(long).closest("details")).not.toBeNull();
});

it("shows nothing when there are no steps", async () => {
  const fetchMock = stubApi({ "/api/claims/CLM-1001/steps": [] });
  const { container } = render(<Steps claimId="CLM-1001" working={false} />);
  await vi.waitFor(() => {
    expect(fetchMock).toHaveBeenCalled();
  });
  expect(container.textContent).toBe("");
});

it("polls every two seconds while the agent works", async () => {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  const fetchMock = stubApi({ "/api/claims/CLM-1001/steps": steps });
  render(<Steps claimId="CLM-1001" working />);
  await vi.advanceTimersByTimeAsync(0);
  const before = fetchMock.mock.calls.length;
  await vi.advanceTimersByTimeAsync(4000);
  expect(fetchMock.mock.calls).toHaveLength(before + 2);
});

it("does not poll when the agent is not working", async () => {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  const fetchMock = stubApi({ "/api/claims/CLM-1001/steps": steps });
  render(<Steps claimId="CLM-1001" working={false} />);
  await vi.advanceTimersByTimeAsync(0);
  const before = fetchMock.mock.calls.length;
  await vi.advanceTimersByTimeAsync(6000);
  expect(fetchMock.mock.calls).toHaveLength(before);
});

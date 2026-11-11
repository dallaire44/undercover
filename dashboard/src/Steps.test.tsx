import { cleanup, render, screen, within } from "@testing-library/react";
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
  const timeline = screen.getByRole("region", { name: "What the agent did" });
  const items = within(timeline)
    .getAllByRole("listitem")
    .map((item) => item.textContent);
  expect(items[0]).toContain("Agent started");
  expect(items[1]).toContain("get_claim");
  expect(items[2]).toContain("short result");
  expect(screen.getByText("Result, 300 characters")).toBeDefined();
  expect(screen.getByText(long).closest("details")).not.toBeNull();
});

it("shows no timeline and no sections read before the agent starts", async () => {
  stubApi({ "/api/claims/CLM-1001/steps": [] });
  render(<Steps claimId="CLM-1001" working={false} />);
  expect(await screen.findByText("None yet.")).toBeDefined();
  expect(screen.queryByText("What the agent did")).toBeNull();
});

it("lists the sections the agent read, in order", async () => {
  stubApi({
    "/api/claims/CLM-1001/steps": [
      ...steps,
      step(5, "read", "Policy wording, 3. Trip Delay\n\nWe pay when..."),
      step(6, "tool_call", 'read_section({"number": "10"})'),
      step(7, "read", "Claims manual, 10. Meals without receipts\n\nFlat $35."),
    ],
  });
  render(<Steps claimId="CLM-1001" working={false} />);
  const panel = await screen.findByRole("region", { name: "Sections read" });
  const names = within(panel)
    .getAllByRole("listitem")
    .map((item) => item.textContent);
  expect(names).toEqual([
    "Policy wording, 3. Trip Delay",
    "Claims manual, 10. Meals without receipts",
  ]);
  const timeline = screen.getByRole("region", { name: "What the agent did" });
  const folded = within(timeline).getByText("Policy wording, 3. Trip Delay");
  expect(folded.closest("details")).not.toBeNull();
  expect(within(timeline).getAllByText("Read")).toHaveLength(2);
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

import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { EvaluationPage } from "./Evaluation";
import { evaluation, stubApi } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows each claim beside the handler's decision, with the misses marked", async () => {
  stubApi({ "/api/evaluations/RUN-0007": evaluation });
  render(<EvaluationPage runId="RUN-0007" />);
  expect(await screen.findByText("Evaluation RUN-0007")).toBeDefined();
  expect(
    screen.getByText("Held-out set, tiny, 5 claim agents at once"),
  ).toBeDefined();
  expect(screen.getByText("$1,550.00")).toBeDefined();
  const [right, miss] = screen.getAllByRole("row").slice(1);
  expect(within(right).queryByText("Miss")).toBeNull();
  expect(within(right).getByText("Right")).toBeDefined();
  expect(within(miss).getByText("Miss").className).toBe("chip miss-chip");
  expect(within(miss).getByText("Declined")).toBeDefined();
  expect(within(miss).getByText("Referred")).toBeDefined();
  expect(
    within(miss).getByRole("link", { name: "CLM-1114" }).getAttribute("href"),
  ).toBe("#/claims/RUN-0007-CLM-1114");
  expect(within(right).getAllByText("$250.00")).toHaveLength(2);
});

it("says when the evaluation is not found", async () => {
  stubApi({});
  render(<EvaluationPage runId="RUN-0099" />);
  expect(
    await screen.findByText("Evaluation RUN-0099 was not found."),
  ).toBeDefined();
});

it("shows why an evaluation stopped", async () => {
  stubApi({
    "/api/evaluations/RUN-0007": {
      ...evaluation,
      run: {
        ...evaluation.run,
        status: "stopped",
        reason: "The agent's service restarted",
      },
    },
  });
  render(<EvaluationPage runId="RUN-0007" />);
  expect(
    await screen.findByText(
      "openai/gpt-6-luna, low effort. Stopped: The agent's service restarted",
    ),
  ).toBeDefined();
});

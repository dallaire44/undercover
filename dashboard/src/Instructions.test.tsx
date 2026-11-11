import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "./fixtures";
import { Instructions } from "./Instructions";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows both agents' instructions read only", async () => {
  stubApi({
    "/api/instructions/queue": "# Running the queue\n\nPlan the run.",
    "/api/instructions/claim": "# Working a claim\n\nDecide.",
  });
  render(<Instructions />);
  const queue = screen.getByRole("region", { name: "Running the queue" });
  const claim = screen.getByRole("region", { name: "Working a claim" });
  expect(await within(queue).findByText(/Plan the run\./)).toBeDefined();
  expect(await within(claim).findByText(/Decide\./)).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when the instructions cannot be loaded", async () => {
  stubApi({});
  render(<Instructions />);
  expect(
    await screen.findAllByText("The instructions could not be loaded."),
  ).toHaveLength(2);
});

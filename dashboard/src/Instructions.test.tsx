import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "./fixtures";
import { Instructions } from "./Instructions";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the claim agent's instructions read only, in one panel", async () => {
  stubApi({ "/api/instructions/claim": "# Working a claim\n\nDecide." });
  render(<Instructions />);
  const claim = screen.getByRole("region", { name: "Working a claim" });
  expect(await within(claim).findByText(/Decide\./)).toBeDefined();
  expect(screen.getAllByRole("region")).toHaveLength(1);
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when the instructions cannot be loaded", async () => {
  stubApi({});
  render(<Instructions />);
  expect(
    await screen.findByText("The instructions could not be loaded."),
  ).toBeDefined();
});

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "./fixtures";
import { Instructions } from "./Instructions";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the instructions read only", async () => {
  stubApi({
    "/api/instructions": "# UnderCover Agent: instructions\n\nDecide.",
  });
  render(<Instructions />);
  expect(
    await screen.findByText(/UnderCover Agent: instructions/),
  ).toBeDefined();
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

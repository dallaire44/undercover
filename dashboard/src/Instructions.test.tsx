import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubFetch } from "./fixtures";
import { Instructions } from "./Instructions";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the agent's instructions, read only", async () => {
  const text =
    "# Instructions for the UnderCover Agent\n\nRead the claim first.";
  vi.stubGlobal("fetch", stubFetch({ "/api/instructions": { text } }));
  render(<Instructions />);
  expect(await screen.findByText(/Read the claim first/)).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when the instructions could not be loaded", async () => {
  vi.stubGlobal("fetch", stubFetch({}));
  render(<Instructions />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "could not be loaded",
  );
});

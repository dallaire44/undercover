import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { claim, history, policy, queue, stubFetch } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

const routes = {
  "/api/claims": queue,
  "/api/instructions": { text: "Read the claim first." },
  "/api/claims/CLM-1001": claim,
  "/api/policies/POL-2001": policy,
  "/api/customers/CUS-3001/history": history,
};

it("shows the name, the tagline and the queue", async () => {
  vi.stubGlobal("fetch", stubFetch(routes));
  render(<App />);
  expect(screen.getByRole("heading", { name: "UnderCover" })).toBeDefined();
  expect(screen.getByText(/Every claim decided/)).toBeDefined();
  expect(await screen.findByText("CLM-1002")).toBeDefined();
});

it("opens a claim from its hash link, and goes back to the queue", async () => {
  vi.stubGlobal("fetch", stubFetch(routes));
  window.location.hash = "#/claims/CLM-1001";
  render(<App />);
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  act(() => {
    window.location.hash = "#/";
  });
  expect(await screen.findByText("CLM-1002")).toBeDefined();
});

it("opens the agent's instructions from the header", async () => {
  vi.stubGlobal("fetch", stubFetch(routes));
  window.location.hash = "#/instructions";
  render(<App />);
  expect(await screen.findByText("Read the claim first.")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Agent instructions" })
      .getAttribute("href"),
  ).toBe("#/instructions");
});

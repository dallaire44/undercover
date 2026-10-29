import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { detail, history, policy, stubApi, waitingClaim } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("shows the queue", async () => {
  stubApi({ "/api/claims": [waitingClaim] });
  render(<App />);
  expect(await screen.findByText("CLM-1001")).toBeDefined();
  expect(screen.getByText("Every claim, read closely.")).toBeDefined();
});

it("says when the queue cannot be loaded", async () => {
  stubApi({});
  render(<App />);
  expect(
    await screen.findByText("The claims could not be loaded."),
  ).toBeDefined();
});

it("opens a claim from its hash", async () => {
  stubApi({
    "/api/claims/CLM-1001": detail,
    "/api/policies/POL-2001": policy,
    "/api/customers/CUS-3001/history": history,
  });
  window.location.hash = "#/claims/CLM-1001";
  render(<App />);
  expect(await screen.findByText("Back to the queue")).toBeDefined();
});

it("follows the hash when it changes", async () => {
  stubApi({ "/api/claims": [waitingClaim], "/api/claims/CLM-1001": detail });
  render(<App />);
  await screen.findByText("Claims queue");
  window.location.hash = "#/claims/CLM-1001";
  expect(await screen.findByText("Back to the queue")).toBeDefined();
});

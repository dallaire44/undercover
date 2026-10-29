import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Claim } from "./Claim";
import { decidedDetail, detail, history, policy, stubApi } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const related = {
  "/api/policies/POL-2001": policy,
  "/api/customers/CUS-3001/history": history,
};

it("shows the claim in full without a decision", async () => {
  stubApi({ "/api/claims/CLM-1001": detail, ...related });
  render(<Claim claimId="CLM-1001" />);
  expect(await screen.findByText("Maya Patel")).toBeDefined();
  expect(
    screen.getByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("$245.00")).toBeDefined();
  expect(screen.getByText("Hotel receipt")).toBeDefined();
  expect(await screen.findByText("Premium")).toBeDefined();
  expect(await screen.findByText(/CLM-0412/)).toBeDefined();
  expect(screen.queryByText("Decision")).toBeNull();
});

it("shows the decision, payment and sign-off", async () => {
  stubApi({ "/api/claims/CLM-1001": decidedDetail, ...related });
  render(<Claim claimId="CLM-1001" />);
  expect(await screen.findByText("Decision")).toBeDefined();
  expect(screen.getByText("Approved")).toBeDefined();
  expect(screen.getByText("The wording covers it.")).toBeDefined();
  expect(screen.getByText("Policy section: 3. Trip Delay")).toBeDefined();
  expect(screen.getByText(/Signed off by Dana Whitfield/)).toBeDefined();
  expect(screen.getByText("Payout $420.00")).toBeDefined();
  expect(screen.getByText(/^Paid/).textContent).toContain("$420.00");
});

it("says when the claim is not found", async () => {
  stubApi({});
  render(<Claim claimId="CLM-9999" />);
  expect(
    await screen.findByText("Claim CLM-9999 was not found."),
  ).toBeDefined();
});

it("runs the agent on a waiting claim and reloads", async () => {
  const fetchMock = stubApi({
    "/api/claims/CLM-1001": detail,
    "/api/claims/CLM-1001/steps": [],
    "/api/claims/CLM-1001/agent": null,
    ...related,
  });
  render(<Claim claimId="CLM-1001" />);
  fireEvent.click(await screen.findByRole("button", { name: "Run the agent" }));
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/claims/CLM-1001/agent",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

it("has no run button once the claim is decided", async () => {
  stubApi({ "/api/claims/CLM-1001": decidedDetail, ...related });
  render(<Claim claimId="CLM-1001" />);
  await screen.findByText("Decision");
  expect(screen.queryByRole("button", { name: "Run the agent" })).toBeNull();
});

it("polls the claim while the agent works", async () => {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  const fetchMock = stubApi({
    "/api/claims/CLM-1001": { ...detail, status: "in_progress" },
    "/api/claims/CLM-1001/steps": [],
    ...related,
  });
  render(<Claim claimId="CLM-1001" />);
  await vi.advanceTimersByTimeAsync(0);
  const claimCalls = () =>
    fetchMock.mock.calls.filter(([path]) => path === "/api/claims/CLM-1001")
      .length;
  const before = claimCalls();
  await vi.advanceTimersByTimeAsync(4000);
  expect(claimCalls()).toBeGreaterThanOrEqual(before + 2);
});

it("shows the sign-off panel for a payment on hold", async () => {
  stubApi({
    "/api/claims/CLM-1001": {
      ...decidedDetail,
      status: "awaiting_sign_off",
      payment: null,
      sign_off: null,
    },
    "/api/handlers": [],
    ...related,
  });
  render(<Claim claimId="CLM-1001" />);
  expect(await screen.findByText("Payment on hold")).toBeDefined();
});

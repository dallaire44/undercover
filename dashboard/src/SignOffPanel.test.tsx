import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ClaimDetail } from "./api";
import { decidedDetail, detail, handlers, stubApi } from "./fixtures";
import { SignOffPanel } from "./SignOffPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const onHold: ClaimDetail = {
  ...decidedDetail,
  status: "awaiting_sign_off",
  decision: {
    decision: "approve",
    payout: 3750,
    reason: "Covered.",
    policy_section: "7. Emergency Medical",
    decided_at: "2026-06-25T10:00:00+00:00",
  },
  payment: null,
  sign_off: null,
};

it("says the payment is on hold and offers the handlers", async () => {
  stubApi({ "/api/handlers": handlers });
  render(<SignOffPanel claim={onHold} onSignedOff={vi.fn()} />);
  expect(screen.getByText("Payment on hold")).toBeDefined();
  expect(screen.getByText("$3,750.00")).toBeDefined();
  expect(
    await screen.findByRole("option", { name: "Priya Raman" }),
  ).toBeDefined();
});

it("signs off as the chosen handler", async () => {
  const fetchMock = stubApi({
    "/api/handlers": handlers,
    "/api/claims/CLM-1001/sign-off": {},
  });
  const onSignedOff = vi.fn();
  render(<SignOffPanel claim={onHold} onSignedOff={onSignedOff} />);
  await screen.findByRole("option", { name: "Priya Raman" });
  fireEvent.change(screen.getByRole("combobox", { name: "Handler" }), {
    target: { value: "HND-03" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  await waitFor(() => {
    expect(onSignedOff).toHaveBeenCalled();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/sign-off",
    expect.objectContaining({ body: '{"handler_id":"HND-03"}' }),
  );
});

it("signs off as the first handler by default", async () => {
  const fetchMock = stubApi({
    "/api/handlers": handlers,
    "/api/claims/CLM-1001/sign-off": {},
  });
  render(<SignOffPanel claim={onHold} onSignedOff={vi.fn()} />);
  await screen.findByRole("option", { name: "Priya Raman" });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/claims/CLM-1001/sign-off",
      expect.objectContaining({ body: '{"handler_id":"HND-01"}' }),
    );
  });
});

it("shows nothing unless the claim waits for sign-off", () => {
  stubApi({ "/api/handlers": handlers });
  const { container } = render(
    <SignOffPanel claim={detail} onSignedOff={vi.fn()} />,
  );
  expect(container.textContent).toBe("");
});

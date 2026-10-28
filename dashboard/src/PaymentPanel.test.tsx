import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { decidedClaim, handlers, stubFetch } from "./fixtures";
import { PaymentPanel } from "./PaymentPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("holds the payment and lists the handlers", async () => {
  vi.stubGlobal("fetch", stubFetch({ "/api/handlers": handlers }));
  render(<PaymentPanel claim={decidedClaim} onSignedOff={vi.fn()} />);
  expect(screen.getByText(/Payment on hold/)).toBeDefined();
  expect(
    await screen.findByRole("option", { name: "Priya Raman" }),
  ).toBeDefined();
  expect(screen.getAllByRole("option")).toHaveLength(3);
});

it("signs off as the chosen handler", async () => {
  const signOff = vi.fn((init?: RequestInit) => ({
    ...decidedClaim,
    body: init?.body,
  }));
  vi.stubGlobal(
    "fetch",
    stubFetch({
      "/api/handlers": handlers,
      "POST /api/claims/CLM-1001/sign-off": signOff,
    }),
  );
  const onSignedOff = vi.fn();
  render(<PaymentPanel claim={decidedClaim} onSignedOff={onSignedOff} />);
  await screen.findByRole("option", { name: "Priya Raman" });
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "HND-03" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  await vi.waitFor(() => {
    expect(onSignedOff).toHaveBeenCalled();
  });
  expect(signOff.mock.calls[0]?.[0]?.body).toBe(
    JSON.stringify({ handler_id: "HND-03" }),
  );
});

it("shows why a sign-off was refused", async () => {
  const refused = () =>
    new Response(
      JSON.stringify({ detail: "The claim is not waiting for sign-off" }),
      { status: 409 },
    );
  vi.stubGlobal(
    "fetch",
    stubFetch({
      "/api/handlers": handlers,
      "POST /api/claims/CLM-1001/sign-off": refused,
    }),
  );
  render(<PaymentPanel claim={decidedClaim} onSignedOff={vi.fn()} />);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The claim is not waiting for sign-off",
  );
});

it("cannot sign off before the handlers have loaded", () => {
  vi.stubGlobal("fetch", stubFetch({}));
  render(<PaymentPanel claim={decidedClaim} onSignedOff={vi.fn()} />);
  expect(
    screen
      .getByRole("button", { name: "Sign off and pay" })
      .hasAttribute("disabled"),
  ).toBe(true);
});

it("shows nothing for a claim with no payment and no hold", () => {
  const { container } = render(
    <PaymentPanel
      claim={{ ...decidedClaim, status: "waiting" }}
      onSignedOff={vi.fn()}
    />,
  );
  expect(container.textContent).toBe("");
});

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { StatusChip, VerdictChip } from "./Chips";

afterEach(cleanup);

it.each([
  ["approve", "Approved", "state-decided"],
  ["decline", "Declined", "state-in_progress"],
  ["refer", "Referred", "state-awaiting_sign_off"],
] as const)(
  "shows %s with its word, its color and a symbol hidden from screen readers",
  (verdict, word, color) => {
    render(<VerdictChip verdict={verdict} />);
    const chip = screen.getByText(word);
    expect(chip.className).toContain(color);
    expect(chip.textContent).toBe(word);
    const symbol = chip.querySelector("svg");
    expect(symbol?.getAttribute("aria-hidden")).toBe("true");
    expect(symbol?.querySelector("path")?.getAttribute("d")).toBeTruthy();
  },
);

it("gives the three decisions three different symbols", () => {
  const shapes = (["approve", "decline", "refer"] as const).map((verdict) => {
    const { container } = render(<VerdictChip verdict={verdict} />);
    return container.querySelector("path")?.getAttribute("d");
  });
  expect(new Set(shapes).size).toBe(3);
});

it("shows a claim state as a chip with its label", () => {
  render(<StatusChip status="awaiting_sign_off" />);
  expect(screen.getByText("Waiting for sign-off").className).toContain(
    "state-awaiting_sign_off",
  );
});

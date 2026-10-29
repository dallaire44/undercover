import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { Verdict } from "./api";
import { VerdictChip } from "./Chips";

afterEach(cleanup);

const CASES: [Verdict, string][] = [
  ["approve", "Approved"],
  ["decline", "Declined"],
  ["refer", "Referred"],
];

it.each(CASES)(
  "the %s chip has a hidden symbol and only its word",
  (verdict, word) => {
    render(<VerdictChip verdict={verdict} />);
    const chip = screen.getByText(word);
    expect(chip.textContent).toBe(word);
    const symbol = chip.querySelector("svg");
    expect(symbol?.getAttribute("aria-hidden")).toBe("true");
    expect(symbol?.querySelector("path")?.getAttribute("d")).toBeTruthy();
  },
);

it("gives each decision its own shape", () => {
  const shapes = CASES.map(([verdict]) => {
    const { container } = render(<VerdictChip verdict={verdict} />);
    return container.querySelector("path")?.getAttribute("d");
  });
  expect(new Set(shapes).size).toBe(3);
});

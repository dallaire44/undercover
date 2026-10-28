import { expect, it } from "vitest";
import { date, humanize, money } from "./format";

it("formats money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
  expect(money(245)).toBe("$245.00");
  expect(money(3750.5)).toBe("$3,750.50");
});

it("formats a date without moving it across a time zone", () => {
  expect(date("2026-06-24")).toBe("Jun 24, 2026");
  expect(date("2026-01-01")).toBe("Jan 1, 2026");
});

it("turns an API word into a label", () => {
  expect(humanize("trip_delay")).toBe("Trip delay");
  expect(humanize("pre_existing_waiver")).toBe("Pre existing waiver");
});

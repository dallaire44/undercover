import { expect, it } from "vitest";
import { date, dateTime, money, titleCase } from "./format";

it("formats money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
  expect(money(245.5)).toBe("$245.50");
});

it("formats a date without shifting the day", () => {
  expect(date("2026-06-24")).toBe("Jun 24, 2026");
});

it("turns a snake case word into a label", () => {
  expect(titleCase("trip_delay")).toBe("Trip delay");
});

it("formats a date and time in UTC", () => {
  expect(dateTime("2026-06-25T14:02:09+00:00")).toBe("Jun 25, 2026, 14:02 UTC");
});

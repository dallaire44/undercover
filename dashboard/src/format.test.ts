import { expect, it } from "vitest";
import { date, dateTime, duration, money, percent, titleCase } from "./format";

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

it("formats a time in minutes and seconds", () => {
  expect(duration(72.4)).toBe("1 min 12 s");
  expect(duration(45)).toBe("45 s");
  expect(duration(0)).toBe("0 s");
});

it("formats a share as a percentage", () => {
  expect(percent(0.8)).toBe("80%");
  expect(percent(2 / 3)).toBe("67%");
});

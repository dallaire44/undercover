import { expect, it } from "vitest";
import { parse } from "./route";

it("reads a claim from the hash", () => {
  expect(parse("#/claims/CLM-1001")).toEqual({ page: "claim", id: "CLM-1001" });
});

it("shows the queue for anything else", () => {
  expect(parse("")).toEqual({ page: "queue" });
  expect(parse("#/")).toEqual({ page: "queue" });
  expect(parse("#/somewhere/else")).toEqual({ page: "queue" });
});

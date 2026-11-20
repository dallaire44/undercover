import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { evaluation, stubApi } from "./fixtures";
import { Scoreboard } from "./Scoreboard";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const older = {
  ...evaluation,
  run: { ...evaluation.run, run_id: "RUN-0003", tiny: false, agents: 25 },
};

it("lists the evaluations newest first with their measures", async () => {
  stubApi({ "/api/evaluations": [evaluation, older] });
  render(<Scoreboard />);
  const rows = (await screen.findAllByRole("row")).slice(1);
  expect(
    rows.map((row) => within(row).getAllByRole("cell")[0].textContent),
  ).toEqual(["RUN-0007", "RUN-0003"]);
  const cells = within(rows[0])
    .getAllByRole("cell")
    .map((cell) => cell.textContent);
  expect(cells).toEqual([
    "RUN-0007",
    "Held-out set, tiny",
    "5",
    "openai/gpt-6-luna, low effort",
    "Finished",
    "80%",
    "60%",
    "$1,550.00",
    "80%",
    "$0.02",
    "42 s",
    "1 min 15 s",
  ]);
  expect(
    within(rows[0])
      .getByRole("link", { name: "RUN-0007" })
      .getAttribute("href"),
  ).toBe("#/scoreboard/RUN-0007");
});

it("says when there are no evaluations yet", async () => {
  stubApi({ "/api/evaluations": [] });
  render(<Scoreboard />);
  expect(await screen.findByText("None yet.")).toBeDefined();
});

it("says when the evaluations cannot be loaded", async () => {
  stubApi({});
  render(<Scoreboard />);
  expect(
    await screen.findByText("The evaluations could not be loaded."),
  ).toBeDefined();
});

it("starts an evaluation with the set, tiny and N", async () => {
  const fetchMock = stubApi({
    "/api/evaluations": [],
    "/api/evaluations/start": null,
  });
  render(<Scoreboard />);
  fireEvent.change(screen.getByLabelText("Set"), {
    target: { value: "held_out" },
  });
  fireEvent.click(screen.getByLabelText("Only the five tiny claims"));
  fireEvent.change(screen.getByLabelText("Claim agents at once"), {
    target: { value: "5" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Start an evaluation" }));
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/evaluations/start",
      expect.objectContaining({
        method: "POST",
        body: '{"agents":5,"claim_set":"held_out","tiny":true}',
      }),
    );
  });
  expect(screen.queryByRole("alert")).toBeNull();
});

it("shows a refusal with its reason", async () => {
  const busy = { detail: "A dispatch or evaluation is already running" };
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) =>
      Promise.resolve(
        path === "/api/evaluations"
          ? new Response("[]")
          : new Response(JSON.stringify(busy), { status: 409 }),
      ),
    ),
  );
  render(<Scoreboard />);
  fireEvent.click(screen.getByRole("button", { name: "Start an evaluation" }));
  expect((await screen.findByRole("alert")).textContent).toBe(busy.detail);
});

it("says when an evaluation could not be started", async () => {
  stubApi({ "/api/evaluations": [] });
  render(<Scoreboard />);
  fireEvent.click(screen.getByRole("button", { name: "Start an evaluation" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The evaluation could not be started.",
  );
});

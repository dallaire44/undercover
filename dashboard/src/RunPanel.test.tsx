import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { finishedRun, runningRun, stubApi } from "./fixtures";
import { RunPanel } from "./RunPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const LATEST = "/api/dispatches/latest";
const button = () => screen.getByRole("button", { name: "Dispatch the queue" });

it("shows a running dispatch with its claims, cost and time", async () => {
  stubApi({ [LATEST]: runningRun });
  render(<RunPanel toWork={20} onStart={vi.fn()} />);
  expect(
    await screen.findByText("Running, 3 claim agents at once"),
  ).toBeDefined();
  const claims = within(
    screen.getByRole("list", { name: "Claims in this dispatch" }),
  ).getAllByRole("listitem");
  expect(claims.map((claim) => claim.textContent)).toEqual([
    "In progressCLM-1001",
    "DecidedCLM-1014",
  ]);
  expect(
    within(claims[0])
      .getByRole("link", { name: "CLM-1001" })
      .getAttribute("href"),
  ).toBe("#/claims/CLM-1001");
  expect(screen.getByText("Model cost $0.04, time 1 min 12 s")).toBeDefined();
  expect(screen.queryByLabelText("Summary")).toBeNull();
  expect(button().hasAttribute("disabled")).toBe(true);
});

it("shows a finished dispatch with its summary", async () => {
  stubApi({ [LATEST]: finishedRun });
  render(<RunPanel toWork={20} onStart={vi.fn()} />);
  expect(await screen.findByText("Finished")).toBeDefined();
  const summary = screen.getByLabelText("Summary");
  expect(
    Array.from(summary.querySelectorAll("p")).map((line) => line.textContent),
  ).toEqual([
    "Approved 2, declined 1, referred 0.",
    "Waiting for sign-off: CLM-1003 ($3,750.00)",
    "Left for a handler: CLM-1009",
    "Still in progress: CLM-1001",
  ]);
  expect(button().hasAttribute("disabled")).toBe(false);
});

it("shows why a dispatch stopped", async () => {
  stubApi({
    [LATEST]: {
      ...runningRun,
      status: "stopped",
      reason: "The agent's service restarted",
    },
  });
  render(<RunPanel toWork={20} onStart={vi.fn()} />);
  expect(
    await screen.findByText("Stopped: The agent's service restarted"),
  ).toBeDefined();
});

it("shows nothing but the form before the first dispatch", async () => {
  const fetchMock = stubApi({ [LATEST]: null });
  render(<RunPanel toWork={0} onStart={vi.fn()} />);
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalled();
  });
  expect(screen.queryByRole("list")).toBeNull();
  expect(button().hasAttribute("disabled")).toBe(true);
});

it("starts at 3 claim agents and keeps N from 1 to 25", () => {
  stubApi({ [LATEST]: null });
  render(<RunPanel toWork={20} onStart={vi.fn()} />);
  const input = screen.getByLabelText<HTMLInputElement>("Claim agents at once");
  expect(input.value).toBe("3");
  expect([input.min, input.max]).toEqual(["1", "25"]);
  fireEvent.change(input, { target: { value: "40" } });
  expect(input.value).toBe("25");
  fireEvent.change(input, { target: { value: "0" } });
  expect(input.value).toBe("1");
});

it("dispatches the queue with the N the handler chose", async () => {
  const fetchMock = stubApi({ [LATEST]: null, "/api/dispatches/start": null });
  const onStart = vi.fn();
  render(<RunPanel toWork={20} onStart={onStart} />);
  fireEvent.change(screen.getByLabelText("Claim agents at once"), {
    target: { value: "5" },
  });
  fireEvent.click(button());
  await waitFor(() => {
    expect(onStart).toHaveBeenCalled();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/dispatches/start",
    expect.objectContaining({ method: "POST", body: '{"agents":5}' }),
  );
  expect(screen.queryByRole("alert")).toBeNull();
});

it("shows a refusal with its reason", async () => {
  const busy = { detail: "A dispatch or evaluation is already running" };
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) =>
      Promise.resolve(
        path === LATEST
          ? new Response("null")
          : new Response(JSON.stringify(busy), { status: 409 }),
      ),
    ),
  );
  render(<RunPanel toWork={20} onStart={vi.fn()} />);
  fireEvent.click(button());
  expect((await screen.findByRole("alert")).textContent).toBe(busy.detail);
});

it("says when a dispatch could not be started", async () => {
  stubApi({ [LATEST]: null });
  render(<RunPanel toWork={20} onStart={vi.fn()} />);
  fireEvent.click(button());
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The dispatch could not be started.",
  );
});

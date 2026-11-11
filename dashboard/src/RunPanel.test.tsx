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

it("shows a running run with its to-do list", async () => {
  stubApi({ "/api/runs/latest": runningRun });
  render(<RunPanel waiting={20} onStart={vi.fn()} />);
  expect(await screen.findByText("Running, up to 5 claims")).toBeDefined();
  const items = within(screen.getByRole("list", { name: "To-do list" }))
    .getAllByRole("listitem")
    .map((item) => item.textContent);
  expect(items).toEqual([
    "DoneCLM-1001: trip delay, $420.00",
    "In progressCLM-1004: baggage delay, $186.00",
    "Left for a handlerCLM-1009: baggage, $980.00",
    "To doCheck for missed claims",
  ]);
  const button = screen.getByRole("button", { name: "Work the queue" });
  expect(button.hasAttribute("disabled")).toBe(true);
});

it("shows a finished run with its summary", async () => {
  stubApi({ "/api/runs/latest": finishedRun });
  render(<RunPanel waiting={20} onStart={vi.fn()} />);
  expect(await screen.findByText("Finished, 3 claims worked")).toBeDefined();
  expect(
    screen.getByText("Worked 3 claims. Total paid: $420.00."),
  ).toBeDefined();
  const button = screen.getByRole("button", { name: "Work the queue" });
  expect(button.hasAttribute("disabled")).toBe(false);
});

it("shows why a run stopped", async () => {
  stubApi({
    "/api/runs/latest": {
      ...runningRun,
      status: "stopped",
      cap: 1,
      summary: "The backend restarted during the run.",
    },
  });
  render(<RunPanel waiting={20} onStart={vi.fn()} />);
  expect(
    await screen.findByText("Stopped: The backend restarted during the run."),
  ).toBeDefined();
});

it("shows nothing but the form before the first run", async () => {
  const fetchMock = stubApi({ "/api/runs/latest": null });
  render(<RunPanel waiting={0} onStart={vi.fn()} />);
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalled();
  });
  expect(screen.queryByRole("list", { name: "To-do list" })).toBeNull();
  const button = screen.getByRole("button", { name: "Work the queue" });
  expect(button.hasAttribute("disabled")).toBe(true);
});

it("starts a run with the cap the handler chose", async () => {
  const fetchMock = stubApi({ "/api/runs/latest": null, "/api/runs": {} });
  const onStart = vi.fn();
  render(<RunPanel waiting={20} onStart={onStart} />);
  const input = screen.getByLabelText("Claims to work");
  expect((input as HTMLInputElement).value).toBe("5");
  fireEvent.change(input, { target: { value: "3" } });
  fireEvent.click(screen.getByRole("button", { name: "Work the queue" }));
  await waitFor(() => {
    expect(onStart).toHaveBeenCalled();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/runs",
    expect.objectContaining({ method: "POST", body: '{"cap":3}' }),
  );
});

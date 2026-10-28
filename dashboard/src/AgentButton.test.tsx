import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AgentButton } from "./AgentButton";

afterEach(cleanup);

it("starts the agent and says so", async () => {
  const start = vi.fn().mockResolvedValue({});
  const onStarted = vi.fn();
  render(
    <AgentButton label="Run the agent" start={start} onStarted={onStarted} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Run the agent" }));
  await vi.waitFor(() => {
    expect(onStarted).toHaveBeenCalled();
  });
  expect(start).toHaveBeenCalledOnce();
});

it("shows the backend's reason when the agent cannot start", async () => {
  const start = vi
    .fn()
    .mockRejectedValue(new Error("The claim is not waiting"));
  const onStarted = vi.fn();
  render(
    <AgentButton label="Run the agent" start={start} onStarted={onStarted} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Run the agent" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The claim is not waiting",
  );
  expect(onStarted).not.toHaveBeenCalled();
});

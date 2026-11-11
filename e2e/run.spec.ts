import { expect, test, type APIRequestContext } from "@playwright/test";
import { expectCountsMatchChips } from "./helpers";

async function latestRunId(request: APIRequestContext) {
  const run = (await (await request.get("/api/runs/latest")).json()) as {
    run_id: string;
  };
  return run.run_id;
}

const writeTodos = (
  request: APIRequestContext,
  runId: string,
  todos: [string, string][],
) =>
  request.put(`/api/runs/${runId}/todos`, {
    data: {
      todos: todos.map(([content, status]) => ({ content, status })),
    },
  });

test("a run's to-do list fills in and is ticked off", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByLabel("Claims to work").fill("2");
  await page.getByRole("button", { name: "Work the queue" }).click();
  await expect(page.getByText("Running, up to 2 claims")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Work the queue" }),
  ).toBeDisabled();

  const runId = await latestRunId(request);
  await writeTodos(request, runId, [
    ["CLM-1005: passport, $243.00", "in_progress"],
    ["Check for missed claims", "to_do"],
    ["Write the summary", "to_do"],
  ]);
  const list = page.getByRole("list", { name: "To-do list" });
  await expect(list.getByRole("listitem")).toHaveCount(3);
  await expect(list.getByRole("listitem").first()).toContainText("In progress");

  await request.post(`/api/runs/${runId}/claims/CLM-1005`);
  await request.post("/api/claims/CLM-1005/decision", {
    data: {
      decision: "decline",
      payout: 0,
      reason: "The wording does not cover it.",
      policy_section: "6. Passport and Travel Documents",
    },
  });
  await writeTodos(request, runId, [
    ["CLM-1005: passport, $243.00", "done"],
    ["Check for missed claims", "done"],
    ["Write the summary", "done"],
  ]);
  await expect(list.getByRole("listitem").first()).toContainText("Done");

  const blocked = await request.post(`/api/runs/${runId}/finish`, {
    data: { summary: "Too soon." },
  });
  expect(blocked.status()).toBe(409);
  await request.post(`/api/runs/${runId}/claims/CLM-1007`);
  await request.post("/api/claims/CLM-1007/decision", {
    data: {
      decision: "refer",
      payout: 0,
      reason: "The police report is missing.",
      policy_section: "5. Baggage and Personal Effects",
    },
  });
  await request.post(`/api/runs/${runId}/finish`, {
    data: { summary: "Worked 2 claims: 1 declined, 1 referred." },
  });
  await expect(page.getByText("Finished, 2 claims worked")).toBeVisible();
  await expect(
    page.getByText("Worked 2 claims: 1 declined, 1 referred."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Work the queue" }),
  ).toBeEnabled();
  const row = page.getByRole("row", { name: /CLM-1008/ });
  await expect(row.getByRole("cell").nth(5)).toHaveText("Waiting");
});

test("a claim that fails twice needs a handler", async ({ page, request }) => {
  await request.post("/api/runs", { data: { cap: 1 } });
  const runId = await latestRunId(request);
  for (const attempt of [1, 2]) {
    await request.post(`/api/runs/${runId}/claims/CLM-1006`);
    await request.post("/api/claims/CLM-1006/return", {
      data: { thread_id: "e2e", reason: `Attempt ${String(attempt)} failed.` },
    });
  }
  await request.post(`/api/runs/${runId}/finish`, {
    data: { summary: "CLM-1006 was left for a handler." },
  });

  await page.goto("/");
  const cells = page.getByRole("row", { name: /CLM-1006/ }).getByRole("cell");
  await expect(cells.nth(5)).toHaveText("Needs a handler");
  await expectCountsMatchChips(page);
});

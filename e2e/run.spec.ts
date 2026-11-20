import { expect, test, type APIRequestContext } from "@playwright/test";
import { AGENT } from "../playwright.config";
import { expectCountsMatchChips } from "./helpers";

const DISPATCH = {
  agents: 3,
  model: "openai/gpt-6-luna",
  reasoning_effort: "low",
};

async function createDispatch(request: APIRequestContext) {
  const response = await request.post("/api/dispatches", { data: DISPATCH });
  return ((await response.json()) as { run_id: string }).run_id;
}

async function work(
  request: APIRequestContext,
  runId: string,
  claimId: string,
  decision: string,
) {
  await request.post(`/api/runs/${runId}/claims/${claimId}`);
  await request.post(`/api/claims/${claimId}/model-calls`, {
    data: { run_id: runId, input_tokens: 900, output_tokens: 90, cost: 0.02 },
  });
  await request.post(`/api/claims/${claimId}/work-times`, {
    data: {
      run_id: runId,
      started_at: "2026-11-19T10:00:00.000+00:00",
      seconds: 36,
    },
  });
  await request.post(`/api/claims/${claimId}/decision`, {
    data: {
      decision,
      payout: 0,
      reason: "The wording settles it.",
      policy_section: "6. Passport and Travel Documents",
    },
  });
}

test("a dispatch started on the dashboard reaches the agent with N", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByLabel("Claim agents at once").fill("5");
  await page.getByRole("button", { name: "Dispatch the queue" }).click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`${AGENT}/calls`)).json()) as string[],
    )
    .toContain('POST /dispatches {"agents":5}');
});

test("a dispatch's claims, cost and summary show as it goes", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const runId = await createDispatch(request);
  await expect(page.getByText("Running, 3 claim agents at once")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Dispatch the queue" }),
  ).toBeDisabled();

  await request.post(`/api/runs/${runId}/claims/CLM-1005`);
  const claims = page.getByRole("list", { name: "Claims in this dispatch" });
  await expect(claims.getByRole("listitem")).toHaveText([
    "In progressCLM-1005",
  ]);

  await work(request, runId, "CLM-1005", "decline");
  await work(request, runId, "CLM-1007", "refer");
  await expect(claims.getByRole("listitem")).toHaveText([
    "DecidedCLM-1005",
    "DecidedCLM-1007",
  ]);
  await expect(
    page.getByText(/^Model cost \$0\.04, time \d+ s$/),
  ).toBeVisible();

  await request.post(`/api/runs/${runId}/finish`);
  await expect(page.getByText("Finished", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Approved 0, declined 1, referred 1."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Dispatch the queue" }),
  ).toBeEnabled();
  await claims.getByRole("link", { name: "CLM-1007" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1007$/);
});

test("a claim that fails twice needs a handler", async ({ page, request }) => {
  const runId = await createDispatch(request);
  for (const attempt of [1, 2]) {
    await request.post(`/api/runs/${runId}/claims/CLM-1006`);
    await request.post("/api/claims/CLM-1006/return", {
      data: { thread_id: "e2e", reason: `Attempt ${String(attempt)} failed.` },
    });
  }
  await request.post(`/api/runs/${runId}/finish`);

  await page.goto("/");
  await expect(page.getByText("Left for a handler: CLM-1006")).toBeVisible();
  const cells = page.getByRole("row", { name: /CLM-1006/ }).getByRole("cell");
  await expect(cells.nth(5)).toHaveText("Needs a handler");
  await expectCountsMatchChips(page);
});

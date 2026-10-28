import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

const API = "http://127.0.0.1:8001";

test("a payout over the limit waits for a handler, who signs it off", async ({
  page,
  request,
}) => {
  const decision = await request.post(`${API}/api/claims/CLM-1012/decision`, {
    data: {
      decision: "approve",
      payout: 2400,
      reason: "The baggage loss is covered, less the deductible.",
      policy_section: "Section 5, Baggage and Personal Effects",
    },
  });
  expect(decision.ok()).toBe(true);
  const payment = await request.post(`${API}/api/claims/CLM-1012/payment`, {
    data: { amount: 2400 },
  });
  expect(payment.status()).toBe(409);

  await page.goto("/#/claims/CLM-1012");
  await expect(
    page.getByText("Waiting for sign-off", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Payment on hold/)).toBeVisible();

  await page.getByLabel("Handler").selectOption({ label: "Priya Raman" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(page.getByText("Signed off by Priya Raman")).toBeVisible();
  await expect(page.getByText(/Paid \$2,400\.00/)).toBeVisible();
  await expect(page.getByText("Decided", { exact: true })).toBeVisible();
  await expect(page.getByText(/Payment on hold/)).toBeHidden();

  await page.getByRole("link", { name: "Back to the queue" }).click();
  const row = page.getByRole("row", { name: /CLM-1012/ });
  await expect(row.getByText("Decided", { exact: true })).toBeVisible();
  await expect(row.getByText("$2,400.00")).toBeVisible();
});

test("steps posted through the API show on the claim in order", async ({
  page,
  request,
}) => {
  const texts = [
    "Agent started",
    'get_claim({"claim_id": "CLM-1015"})',
    "Agent finished",
  ];
  const kinds = ["message", "tool_call", "message"];
  for (const [i, text] of texts.entries()) {
    const response = await request.post(`${API}/api/claims/CLM-1015/steps`, {
      data: { thread_id: "e2e", kind: kinds[i], text },
    });
    expect(response.ok()).toBe(true);
  }
  await page.goto("/#/claims/CLM-1015");
  await expect(page.getByText("What the agent did")).toBeVisible();
  await expect(page.locator("ol.steps li")).toHaveText([
    "The agent saysAgent started",
    'Tool callget_claim({"claim_id": "CLM-1015"})',
    "The agent saysAgent finished",
  ]);
});

test("the instructions page shows the agent's instructions and cannot edit them", async ({
  page,
}) => {
  const file = readFileSync("backend/instructions.md", "utf8").trim();
  await page.goto("/");
  await page.getByRole("link", { name: "Agent instructions" }).click();
  await expect(page).toHaveURL(/#\/instructions$/);
  await expect(page.locator("pre.instructions")).toHaveText(file);
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByRole("button")).toHaveCount(0);
});

test("the agent buttons are there for a waiting claim and the queue", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Work the queue" }),
  ).toBeVisible();
  await page.goto("/#/claims/CLM-1020");
  await expect(
    page.getByRole("button", { name: "Run the agent" }),
  ).toBeVisible();
});

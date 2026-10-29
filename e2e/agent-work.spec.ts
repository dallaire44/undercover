import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { expectCountsMatchChips } from "./helpers";

test("a payout over the limit is blocked until a handler signs off", async ({
  page,
  request,
}) => {
  await request.post("/api/claims/CLM-1012/decision", {
    data: {
      decision: "approve",
      payout: 1500,
      reason: "The wording covers it.",
      policy_section: "5. Baggage",
    },
  });
  const blocked = await request.post("/api/claims/CLM-1012/payment", {
    data: { amount: 1500 },
  });
  expect(blocked.status()).toBe(409);

  await page.goto("/#/claims/CLM-1012");
  await expect(page.getByText("Waiting for sign-off")).toBeVisible();
  await expect(page.getByText("Payment on hold")).toBeVisible();

  await page.getByLabel("Handler").selectOption({ label: "Priya Raman" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(page.getByText("Decided", { exact: true })).toBeVisible();
  await expect(page.getByText(/Signed off by Priya Raman/)).toBeVisible();
  await expect(page.getByText(/^Paid \$1,500\.00/)).toBeVisible();
  await expect(page.getByText("Payment on hold")).toBeHidden();

  await page.goto("/");
  const cells = page.getByRole("row", { name: /CLM-1012/ }).getByRole("cell");
  await expect(cells.nth(5)).toHaveText("Decided");
  await expectCountsMatchChips(page);
});

test("the agent's steps show in order", async ({ page, request }) => {
  const steps = [
    ["message", "Agent started"],
    ["tool_call", 'get_claim({"claim_id": "CLM-1018"})'],
    ["tool_result", "The claim, in full."],
  ];
  for (const [kind, text] of steps) {
    await request.post("/api/claims/CLM-1018/steps", {
      data: { thread_id: "e2e", kind, text },
    });
  }
  await page.goto("/#/claims/CLM-1018");
  const items = page
    .getByRole("region", { name: "What the agent did" })
    .getByRole("listitem");
  await expect(items).toHaveCount(3);
  await expect(items.nth(0)).toContainText("Agent started");
  await expect(items.nth(1)).toContainText("get_claim");
  await expect(items.nth(2)).toContainText("The claim, in full.");
});

test("the instructions page shows the instructions and cannot edit them", async ({
  page,
}) => {
  const text = readFileSync("backend/instructions.md", "utf-8");
  await page.goto("/");
  await page.getByRole("link", { name: "Agent instructions" }).click();
  await expect(page.locator("pre")).toHaveText(text.trim());
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByRole("button")).toHaveCount(0);
});

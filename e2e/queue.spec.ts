import { expect, test } from "@playwright/test";
import { expectCountsMatchChips } from "./helpers";

test("the queue shows 25 claims and the counts match the chips", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("tbody tr")).toHaveCount(25);
  await expectCountsMatchChips(page);
});

test("a decision shows in the queue row", async ({ page, request }) => {
  await request.post("/api/claims/CLM-1014/decision", {
    data: {
      decision: "approve",
      payout: 650,
      reason: "The wording covers it.",
      policy_section: "3. Trip Delay",
    },
  });
  await page.goto("/");
  const cells = page.getByRole("row", { name: /CLM-1014/ }).getByRole("cell");
  await expect(cells.nth(6)).toHaveText("Approved");
  await expect(cells.nth(7)).toHaveText("$650.00");
});

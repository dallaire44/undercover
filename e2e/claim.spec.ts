import { expect, test } from "@playwright/test";

test("a claim opens from the queue with its story, items and policy", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
  await expect(page.getByText("Maya Patel", { exact: true })).toBeVisible();
  await expect(page.getByText(/Meridian Air/).first()).toBeVisible();
  await expect(page.getByRole("cell", { name: "$245.00" })).toBeVisible();
  await expect(
    page.getByText("UnderCover Premium", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision" })).toBeHidden();
});

test("a decided claim shows its decision, payout, reason and section", async ({
  page,
  request,
}) => {
  await request.post("/api/claims/CLM-1016/decision", {
    data: {
      decision: "refer",
      payout: 0,
      reason: "A receipt is missing, so a handler should look at it.",
      policy_section: "11. Documents",
    },
  });
  await page.goto("/#/claims/CLM-1016");
  await expect(page.getByRole("heading", { name: "Decision" })).toBeVisible();
  await expect(page.getByText("Referred", { exact: true })).toBeVisible();
  await expect(page.getByText("Payout $0.00")).toBeVisible();
  await expect(page.getByText(/A receipt is missing/)).toBeVisible();
  await expect(page.getByText("Policy section: 11. Documents")).toBeVisible();
});

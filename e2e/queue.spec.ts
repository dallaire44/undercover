import { expect, test } from "@playwright/test";

const STATES = ["Waiting", "In progress", "Waiting for sign-off", "Decided"];

test("the queue shows 25 claims and the counts match the chips", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("tbody tr")).toHaveCount(25);
  const table = page.getByRole("table");
  const tiles = page.getByRole("list", { name: "Claims by status" });
  for (const label of STATES) {
    const tile = tiles
      .getByRole("listitem")
      .filter({ has: page.getByText(label, { exact: true }) });
    const chips = await table.getByText(label, { exact: true }).count();
    await expect(tile.locator("strong")).toHaveText(String(chips));
  }
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

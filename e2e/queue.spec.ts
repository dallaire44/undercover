import { expect, test } from "@playwright/test";

const API = "http://127.0.0.1:8001";
const LABELS = ["Waiting", "In progress", "Waiting for sign-off", "Decided"];

test("the queue shows 25 claims, and each count matches the chips", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("row")).toHaveCount(26);
  for (const label of LABELS) {
    const tile = page
      .getByRole("listitem")
      .filter({ hasText: new RegExp(`${label}$`) });
    const chips = page
      .locator("td:nth-child(6)")
      .filter({ hasText: new RegExp(`^${label}$`) });
    await expect(tile.locator(".number")).toHaveText(
      String(await chips.count()),
    );
  }
});

test("a claim opens with its story, items, policy and history", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
  await expect(page.getByText("My flight home from Rome")).toBeVisible();
  await expect(page.getByRole("cell", { name: "$245.00" })).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(4);
  await expect(page.getByText("Rome, Italy", { exact: true })).toBeVisible();
  await expect(page.getByText("Premium", { exact: true })).toBeVisible();
  await expect(page.getByText(/CLM-0412/)).toBeVisible();
  await page.getByRole("link", { name: "Back to the queue" }).click();
  await expect(page.getByRole("row")).toHaveCount(26);
});

test("a decision recorded through the API shows in the queue and on the claim", async ({
  page,
  request,
}) => {
  const reason = "The wording covers the stated loss.";
  const response = await request.post(`${API}/api/claims/CLM-1014/decision`, {
    data: {
      decision: "approve",
      payout: 650,
      reason,
      policy_section: "Section 5, Baggage and Personal Effects",
    },
  });
  expect(response.ok()).toBe(true);
  await page.goto("/");
  const row = page.getByRole("row", { name: /CLM-1014/ });
  await expect(row.getByText("Approved")).toBeVisible();
  await expect(row.getByText("$650.00")).toBeVisible();
  await row.getByRole("link").click();
  await expect(page.getByText("The agent's decision")).toBeVisible();
  await expect(page.getByText(reason)).toBeVisible();
  await expect(
    page.getByText("Section 5, Baggage and Personal Effects"),
  ).toBeVisible();
  await expect(page.getByText("$650.00")).toBeVisible();
});

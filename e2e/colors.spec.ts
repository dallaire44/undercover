import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const API = "http://127.0.0.1:8001";
const colorBlindSwitch = (page: Page) =>
  page.getByRole("switch", { name: "Color-blind mode" });
const darkSwitch = (page: Page) =>
  page.getByRole("switch", { name: "Dark mode" });

async function decide(
  request: import("@playwright/test").APIRequestContext,
  claim: string,
  decision: string,
  payout: number,
) {
  const response = await request.post(`${API}/api/claims/${claim}/decision`, {
    data: {
      decision,
      payout,
      reason: "Decided for a color check.",
      policy_section: "Section 3",
    },
  });
  expect(response.ok()).toBe(true);
}

const statusChip = (page: Page, label: string) =>
  page
    .locator("td:nth-child(6) .chip")
    .filter({ hasText: new RegExp(`^${label}$`) });

test("with nothing saved the mode is off and the brand is unchanged", async ({
  page,
  request,
}) => {
  await decide(request, "CLM-1016", "decline", 0);
  await page.goto("/");
  await expect(colorBlindSwitch(page)).toHaveAttribute("aria-checked", "false");
  const waiting = statusChip(page, "Waiting").first();
  await expect(waiting).toHaveCSS("background-color", "rgb(17, 138, 178)");
  await expect(waiting).toHaveCSS("color", "rgb(255, 255, 255)");
  await expect(statusChip(page, "Decided").first()).toHaveCSS(
    "background-color",
    "rgb(6, 214, 160)",
  );
  await expect(page.locator(".symbol").first()).toBeHidden();
});

test("the color-blind mode recolors the chips and shows symbols", async ({
  page,
  request,
}) => {
  await decide(request, "CLM-1017", "approve", 1500);
  await decide(request, "CLM-1018", "decline", 0);
  await page.goto("/");
  await colorBlindSwitch(page).click();
  const waiting = statusChip(page, "Waiting").first();
  await expect(waiting).toHaveCSS("background-color", "rgb(0, 114, 178)");
  await expect(waiting).toHaveCSS("color", "rgb(255, 255, 255)");
  const decided = statusChip(page, "Decided").first();
  await expect(decided).toHaveCSS("background-color", "rgb(0, 158, 115)");
  await expect(decided).toHaveCSS("color", "rgb(0, 0, 0)");
  const declined = page
    .getByRole("row", { name: /CLM-1018/ })
    .locator(".chip", {
      hasText: "Declined",
    });
  await expect(declined.locator(".symbol")).toBeVisible();

  await page.goto("/#/claims/CLM-1017");
  const hold = page.locator(".hold");
  await expect(hold).toHaveCSS("background-color", "rgb(204, 121, 167)");
  await expect(hold).toHaveCSS("color", "rgb(0, 0, 0)");
  await expect(page.locator(".symbol")).toBeVisible();

  await page.reload();
  await expect(colorBlindSwitch(page)).toHaveAttribute("aria-checked", "true");
  await colorBlindSwitch(page).click();
  await expect(colorBlindSwitch(page)).toHaveAttribute("aria-checked", "false");
  await expect(hold).toHaveCSS("background-color", "rgb(239, 71, 111)");
  await expect(page.locator(".symbol")).toBeHidden();
});

test("the two switches are independent", async ({ page }) => {
  await page.goto("/");
  await darkSwitch(page).click();
  await colorBlindSwitch(page).click();
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(4, 35, 46)",
  );
  await expect(statusChip(page, "Waiting").first()).toHaveCSS(
    "background-color",
    "rgb(0, 114, 178)",
  );
  await colorBlindSwitch(page).click();
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(4, 35, 46)",
  );
  await expect(statusChip(page, "Waiting").first()).toHaveCSS(
    "background-color",
    "rgb(17, 138, 178)",
  );
  await colorBlindSwitch(page).click();
  await darkSwitch(page).click();
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(240, 244, 245)",
  );
  await expect(statusChip(page, "Waiting").first()).toHaveCSS(
    "background-color",
    "rgb(0, 114, 178)",
  );
});

for (const saved of [undefined, "color-blind", "brand"] as const) {
  test(`no flash: colors saved ${saved ?? "nothing"}`, async ({ page }) => {
    await page.addInitScript((choice: string | undefined) => {
      if (choice) localStorage.setItem("undercover-colors", choice);
      document.addEventListener("readystatechange", () => {
        if (document.readyState === "interactive") {
          (window as unknown as { colorsAtParse: string }).colorsAtParse =
            document.documentElement.dataset.colors ?? "none";
        }
      });
    }, saved);
    await page.goto("/");
    const colors = await page.evaluate(
      () => (window as unknown as { colorsAtParse: string }).colorsAtParse,
    );
    expect(colors).toBe(saved ?? "brand");
  });
}

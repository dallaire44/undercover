import { expect, test, type Page } from "@playwright/test";
import { dotIsRight } from "./helpers";

const colorBlind = (page: Page) =>
  page.getByRole("switch", { name: "Color-blind mode" });
const darkMode = (page: Page) =>
  page.getByRole("switch", { name: "Dark mode" });
const waitingChip = (page: Page) => page.locator(".chip.state-waiting").first();
const row = (page: Page, id: string) =>
  page.getByRole("row", { name: new RegExp(id) });

const WHITE = "rgb(255, 255, 255)";
const BLACK = "rgb(0, 0, 0)";

test.beforeAll(async ({ request }) => {
  const data = { reason: "r", policy_section: "3. Trip Delay" };
  await request.post("/api/claims/CLM-1021/decision", {
    data: { ...data, decision: "decline", payout: 0 },
  });
  await request.post("/api/claims/CLM-1020/decision", {
    data: { ...data, decision: "approve", payout: 650 },
  });
  await request.post("/api/claims/CLM-1019/decision", {
    data: { ...data, decision: "approve", payout: 1500 },
  });
});

test("with nothing saved the mode is off and the brand is unchanged", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-colors", "brand");
  await expect(colorBlind(page)).toHaveAttribute("aria-checked", "false");
  await expect(waitingChip(page)).toHaveCSS(
    "background-color",
    "rgb(17, 138, 178)",
  );
  await expect(waitingChip(page)).toHaveCSS("color", WHITE);
  const decided = row(page, "CLM-1021").locator(".chip.state-decided");
  await expect(decided).toHaveCSS("background-color", "rgb(6, 214, 160)");
  await expect(page.locator(".verdict-symbol").first()).toBeHidden();
});

test("color-blind mode changes the chips, adds symbols and persists", async ({
  page,
}) => {
  await page.goto("/");
  await colorBlind(page).click();
  await expect(waitingChip(page)).toHaveCSS(
    "background-color",
    "rgb(0, 114, 178)",
  );
  await expect(waitingChip(page)).toHaveCSS("color", WHITE);
  const decided = row(page, "CLM-1021").locator(".chip.state-decided");
  await expect(decided).toHaveCSS("background-color", "rgb(0, 158, 115)");
  await expect(decided).toHaveCSS("color", BLACK);
  await expect(row(page, "CLM-1020").locator(".verdict-symbol")).toBeVisible();
  await expect(row(page, "CLM-1021").locator(".verdict-symbol")).toBeVisible();

  await page.goto("/#/claims/CLM-1020");
  await expect(page.locator(".verdict-symbol")).toBeVisible();
  await page.goto("/#/claims/CLM-1019");
  const hold = page.locator(".on-hold");
  await expect(hold).toHaveCSS("background-color", "rgb(204, 121, 167)");
  await expect(hold).toHaveCSS("color", BLACK);

  await page.reload();
  await expect(colorBlind(page)).toHaveAttribute("aria-checked", "true");
  await expect(hold).toHaveCSS("background-color", "rgb(204, 121, 167)");
  await colorBlind(page).click();
  await expect(hold).toHaveCSS("background-color", "rgb(239, 71, 111)");
  await expect(hold).toHaveCSS("color", WHITE);
});

test("the two sliders are independent", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await darkMode(page).click();
  await colorBlind(page).click();
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(4, 35, 46)",
  );
  await expect(waitingChip(page)).toHaveCSS(
    "background-color",
    "rgb(0, 114, 178)",
  );
  await colorBlind(page).click();
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(4, 35, 46)",
  );
  await expect(waitingChip(page)).toHaveCSS(
    "background-color",
    "rgb(17, 138, 178)",
  );
  await colorBlind(page).click();
  await darkMode(page).click();
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(240, 244, 245)",
  );
  await expect(waitingChip(page)).toHaveCSS(
    "background-color",
    "rgb(0, 114, 178)",
  );
});

for (const scheme of ["light", "dark"] as const) {
  test(`each dot is left when off and right when on, in ${scheme}`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto("/");
    const startsOn = scheme === "dark";
    await expect.poll(() => dotIsRight(darkMode(page))).toBe(startsOn);
    await expect.poll(() => dotIsRight(colorBlind(page))).toBe(false);
    await colorBlind(page).click();
    await expect.poll(() => dotIsRight(colorBlind(page))).toBe(true);
    await expect.poll(() => dotIsRight(darkMode(page))).toBe(startsOn);
  });
}

test("Space flips each slider from the keyboard", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await darkMode(page).focus();
  await page.keyboard.press("Space");
  await expect(darkMode(page)).toHaveAttribute("aria-checked", "true");
  await page.keyboard.press("Tab");
  await expect(colorBlind(page)).toBeFocused();
  await page.keyboard.press("Space");
  await expect(colorBlind(page)).toHaveAttribute("aria-checked", "true");
});

const SAVED = [null, "color-blind", "brand"] as const;

for (const saved of SAVED) {
  test(`no flash: colors saved ${saved ?? "nothing"}`, async ({ page }) => {
    await page.addInitScript((choice) => {
      if (choice) localStorage.setItem("undercover-colors", choice);
      document.addEventListener("readystatechange", () => {
        if (document.readyState === "interactive")
          (window as unknown as Record<string, string>).colorsAtParse =
            document.documentElement.dataset.colors ?? "none";
      });
    }, saved);
    await page.goto("/");
    const early = await page.evaluate(
      () => (window as unknown as Record<string, string>).colorsAtParse,
    );
    expect(early).toBe(saved ?? "brand");
  });
}

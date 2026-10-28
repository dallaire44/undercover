import { expect, test } from "@playwright/test";

const LIGHT = "rgb(240, 244, 245)";
const DARK = "rgb(4, 35, 46)";
const switchButton = (page: import("@playwright/test").Page) =>
  page.getByRole("button", { name: "Dark mode" });

test.describe("a computer set to light", () => {
  test.use({ colorScheme: "light" });

  test("starts light, switches to dark, and keeps it", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toHaveCSS("background-color", LIGHT);
    await expect(switchButton(page)).toHaveAttribute("aria-pressed", "false");
    await switchButton(page).click();
    await expect(page.locator("body")).toHaveCSS("background-color", DARK);
    await expect(switchButton(page)).toHaveAttribute("aria-pressed", "true");
    await page.reload();
    await expect(page.locator("body")).toHaveCSS("background-color", DARK);
    await page.getByRole("link", { name: "Agent instructions" }).click();
    await expect(page.locator("body")).toHaveCSS("background-color", DARK);
    await expect(switchButton(page)).toHaveAttribute("aria-pressed", "true");
  });
});

test.describe("a computer set to dark", () => {
  test.use({ colorScheme: "dark" });

  test("starts dark, and remembers a choice of light", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toHaveCSS("background-color", DARK);
    await expect(switchButton(page)).toHaveAttribute("aria-pressed", "true");
    await switchButton(page).click();
    await expect(page.locator("body")).toHaveCSS("background-color", LIGHT);
    await page.reload();
    await expect(page.locator("body")).toHaveCSS("background-color", LIGHT);
    await expect(switchButton(page)).toHaveAttribute("aria-pressed", "false");
  });
});

for (const system of ["light", "dark"] as const) {
  for (const saved of [undefined, "light", "dark"] as const) {
    test(`no flash: computer ${system}, saved ${saved ?? "nothing"}`, async ({
      browser,
    }) => {
      const context = await browser.newContext({
        colorScheme: system,
        baseURL: "http://localhost:5174",
      });
      const page = await context.newPage();
      await page.addInitScript((choice: string | undefined) => {
        if (choice) localStorage.setItem("undercover-theme", choice);
        // Parsing is finished and no script of the app has run yet.
        document.addEventListener("readystatechange", () => {
          if (document.readyState === "interactive") {
            (window as unknown as { modeAtParse: string }).modeAtParse =
              document.documentElement.dataset.theme ?? "none";
          }
        });
      }, saved);
      await page.goto("/");
      const mode = await page.evaluate(
        () => (window as unknown as { modeAtParse: string }).modeAtParse,
      );
      expect(mode).toBe(saved ?? system);
      await context.close();
    });
  }
}

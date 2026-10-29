import { expect, test, type Page } from "@playwright/test";

const LIGHT = "rgb(240, 244, 245)";
const DARK = "rgb(4, 35, 46)";
const slider = (page: Page) => page.getByRole("switch", { name: "Dark mode" });
const background = (page: Page) => page.locator("body");

test.describe("with the computer set to light", () => {
  test.use({ colorScheme: "light" });

  test("starts light, and the slider turns it dark everywhere", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(background(page)).toHaveCSS("background-color", LIGHT);
    await expect(slider(page)).toHaveAttribute("aria-checked", "false");
    await slider(page).click();
    await expect(background(page)).toHaveCSS("background-color", DARK);
    await expect(slider(page)).toHaveAttribute("aria-checked", "true");
    await page.reload();
    await expect(background(page)).toHaveCSS("background-color", DARK);
    await page.getByRole("link", { name: "Agent instructions" }).click();
    await expect(background(page)).toHaveCSS("background-color", DARK);
    await expect(slider(page)).toHaveAttribute("aria-checked", "true");
  });
});

test.describe("with the computer set to dark", () => {
  test.use({ colorScheme: "dark" });

  test("starts dark, and a choice of light is remembered", async ({ page }) => {
    await page.goto("/");
    await expect(background(page)).toHaveCSS("background-color", DARK);
    await expect(slider(page)).toHaveAttribute("aria-checked", "true");
    await slider(page).click();
    await expect(background(page)).toHaveCSS("background-color", LIGHT);
    await page.reload();
    await expect(background(page)).toHaveCSS("background-color", LIGHT);
    await expect(slider(page)).toHaveAttribute("aria-checked", "false");
  });
});

for (const scheme of ["light", "dark"] as const) {
  test(`the dot is left when off and right when on, in ${scheme}`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto("/");
    const dotIsRight = () =>
      page.locator(".switch-dot").evaluate((dot) => {
        const track =
          dot.parentElement?.getBoundingClientRect() ?? new DOMRect();
        const box = dot.getBoundingClientRect();
        return box.x + box.width / 2 > track.x + track.width / 2;
      });
    const startsOn = scheme === "dark";
    const expectDotAt = async (on: boolean) => {
      await expect(slider(page)).toHaveAttribute("aria-checked", String(on));
      await expect.poll(dotIsRight).toBe(on);
    };
    await expectDotAt(startsOn);
    await slider(page).click();
    await expectDotAt(!startsOn);
  });
}

test("the keyboard reaches the slider and Space flips it", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  for (let tab = 0; tab < 4; tab++) {
    await page.keyboard.press("Tab");
  }
  await expect(slider(page)).toBeFocused();
  await expect(slider(page)).toHaveCSS("outline-style", "solid");
  await expect(slider(page)).toHaveCSS("outline-width", "3px");
  await page.keyboard.press("Space");
  await expect(slider(page)).toHaveAttribute("aria-checked", "true");
  await expect(background(page)).toHaveCSS("background-color", DARK);
});

test("reduced motion turns off the dot's transition", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".switch-dot")).toHaveCSS(
    "transition-duration",
    "0s",
  );
});

const COMBINATIONS = [
  { scheme: "light", saved: null, expected: "light" },
  { scheme: "dark", saved: null, expected: "dark" },
  { scheme: "light", saved: "dark", expected: "dark" },
  { scheme: "dark", saved: "light", expected: "light" },
] as const;

for (const { scheme, saved, expected } of COMBINATIONS) {
  test(`no flash: ${scheme} computer, saved ${saved ?? "nothing"}`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.addInitScript((choice) => {
      if (choice) localStorage.setItem("undercover-theme", choice);
      document.addEventListener("readystatechange", () => {
        if (document.readyState === "interactive")
          (window as unknown as Record<string, string>).themeAtParse =
            document.documentElement.dataset.theme ?? "none";
      });
    }, saved);
    await page.goto("/");
    const early = await page.evaluate(
      () => (window as unknown as Record<string, string>).themeAtParse,
    );
    expect(early).toBe(expected);
  });
}

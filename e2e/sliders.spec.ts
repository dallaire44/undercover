import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";

const NAMES = ["Dark mode", "Color-blind mode"] as const;
const slider = (page: Page, name: (typeof NAMES)[number]) =>
  page.getByRole("switch", { name });

/** Where the dot is on its track: left of center is off, right of center is on. */
async function dotSide(page: Page, name: (typeof NAMES)[number]) {
  const track = await slider(page, name).locator(".track").boundingBox();
  const dot = await slider(page, name).locator(".dot").boundingBox();
  if (!track || !dot) throw new Error(`No slider drawn for ${name}`);
  return dot.x + dot.width / 2 < track.x + track.width / 2 ? "left" : "right";
}

/** Press Tab until the element has focus. */
async function tabTo(page: Page, target: Locator) {
  for (let i = 0; i < 12; i++) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
}

for (const theme of ["light", "dark"] as const) {
  for (const colors of ["brand", "color-blind"] as const) {
    test(`the dot is left when off and right when on: ${theme}, ${colors}`, async ({
      page,
    }) => {
      await page.addInitScript(
        ([t, c]) => {
          localStorage.setItem("undercover-theme", t);
          localStorage.setItem("undercover-colors", c);
        },
        [theme, colors],
      );
      await page.goto("/");
      const darkOn = theme === "dark";
      const colorsOn = colors === "color-blind";
      await expect(slider(page, "Dark mode")).toHaveAttribute(
        "aria-checked",
        String(darkOn),
      );
      await expect(slider(page, "Color-blind mode")).toHaveAttribute(
        "aria-checked",
        String(colorsOn),
      );
      await expect
        .poll(() => dotSide(page, "Dark mode"))
        .toBe(darkOn ? "right" : "left");
      await expect
        .poll(() => dotSide(page, "Color-blind mode"))
        .toBe(colorsOn ? "right" : "left");
    });
  }
}

test("clicking a slider moves its dot across, and clicking again moves it back", async ({
  page,
}) => {
  await page.goto("/");
  for (const name of NAMES) {
    await expect.poll(() => dotSide(page, name)).toBe("left");
    await slider(page, name).click();
    await expect.poll(() => dotSide(page, name)).toBe("right");
    await slider(page, name).click();
    await expect.poll(() => dotSide(page, name)).toBe("left");
  }
});

test("the keyboard reaches each slider, Space flips it, and a focus ring shows", async ({
  page,
}) => {
  await page.goto("/");
  for (const name of NAMES) {
    const target = slider(page, name);
    await tabTo(page, target);
    await expect(target).toBeFocused();
    await expect(target).toHaveCSS("outline-style", "solid");
    await expect(target).toHaveAttribute("aria-checked", "false");
    await page.keyboard.press("Space");
    await expect(target).toHaveAttribute("aria-checked", "true");
    await expect.poll(() => dotSide(page, name)).toBe("right");
  }
});

test("the dot moves with a short transition", async ({ page }) => {
  await page.goto("/");
  await expect(slider(page, "Dark mode").locator(".dot")).toHaveCSS(
    "transition-duration",
    "0.15s",
  );
});

test.describe("a computer set to reduce motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("the dot does not animate", async ({ page }) => {
    await page.goto("/");
    await expect(slider(page, "Dark mode").locator(".dot")).toHaveCSS(
      "transition-duration",
      "0s",
    );
  });
});

import { expect, type Locator, type Page } from "@playwright/test";

const STATES = ["Waiting", "In progress", "Waiting for sign-off", "Decided"];

/** Each state's count tile equals the number of that state's chips in the table. */
export async function expectCountsMatchChips(page: Page) {
  const table = page.getByRole("table");
  const tiles = page.getByRole("list", { name: "Claims by status" });
  for (const label of STATES) {
    const tile = tiles
      .getByRole("listitem")
      .filter({ has: page.getByText(label, { exact: true }) });
    const chips = await table.getByText(label, { exact: true }).count();
    await expect(tile.locator("strong")).toHaveText(String(chips));
  }
}

/** True when the slider's dot is right of the track's center. */
export const dotIsRight = (slider: Locator) =>
  slider.locator(".switch-dot").evaluate((dot) => {
    const track = dot.parentElement?.getBoundingClientRect() ?? new DOMRect();
    const box = dot.getBoundingClientRect();
    return box.x + box.width / 2 > track.x + track.width / 2;
  });

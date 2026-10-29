import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it } from "vitest";
import { ModeSwitch } from "./ModeSwitch";

const root = document.documentElement;

const dark = (
  <ModeSwitch
    label="Dark mode"
    attribute="data-theme"
    on="dark"
    off="light"
    storageKey="undercover-theme"
  />
);
const colors = (
  <ModeSwitch
    label="Color-blind mode"
    attribute="data-colors"
    on="color-blind"
    off="brand"
    storageKey="undercover-colors"
  />
);

beforeEach(() => {
  root.dataset.theme = "light";
  root.dataset.colors = "brand";
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete root.dataset.theme;
  delete root.dataset.colors;
});

const slider = (name: string) => screen.getByRole("switch", { name });

it("is a switch named for its label, off when the attribute is off", () => {
  render(dark);
  expect(slider("Dark mode").getAttribute("aria-checked")).toBe("false");
});

it("starts on when the attribute is on", () => {
  root.dataset.colors = "color-blind";
  render(colors);
  expect(slider("Color-blind mode").getAttribute("aria-checked")).toBe("true");
});

it("flips the attribute, saves the choice and flips back", () => {
  render(dark);
  fireEvent.click(slider("Dark mode"));
  expect(slider("Dark mode").getAttribute("aria-checked")).toBe("true");
  expect(root.dataset.theme).toBe("dark");
  expect(localStorage.getItem("undercover-theme")).toBe("dark");
  fireEvent.click(slider("Dark mode"));
  expect(slider("Dark mode").getAttribute("aria-checked")).toBe("false");
  expect(root.dataset.theme).toBe("light");
  expect(localStorage.getItem("undercover-theme")).toBe("light");
});

it("works for color-blind mode under its own key, leaving dark mode alone", () => {
  render(
    <>
      {dark}
      {colors}
    </>,
  );
  fireEvent.click(slider("Color-blind mode"));
  expect(root.dataset.colors).toBe("color-blind");
  expect(localStorage.getItem("undercover-colors")).toBe("color-blind");
  expect(root.dataset.theme).toBe("light");
  expect(localStorage.getItem("undercover-theme")).toBeNull();
  expect(slider("Dark mode").getAttribute("aria-checked")).toBe("false");
});

it("hides the dot from screen readers", () => {
  const { container } = render(dark);
  const dot = container.querySelector(".switch-dot");
  expect(dot?.getAttribute("aria-hidden")).toBe("true");
});

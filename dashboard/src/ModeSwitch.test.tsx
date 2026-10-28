import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ModeSwitch } from "./ModeSwitch";

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.colors;
});

const dark = (
  <ModeSwitch
    label="Dark mode"
    attribute="theme"
    on="dark"
    off="light"
    storageKey="undercover-theme"
  />
);
const colorBlind = (
  <ModeSwitch
    label="Color-blind mode"
    attribute="colors"
    on="color-blind"
    off="brand"
    storageKey="undercover-colors"
  />
);
const button = (name: string) => screen.getByRole("button", { name });
const html = document.documentElement.dataset;

it("is off while the page is in the other mode", () => {
  html.theme = "light";
  html.colors = "brand";
  render(
    <>
      {dark}
      {colorBlind}
    </>,
  );
  expect(button("Dark mode").getAttribute("aria-pressed")).toBe("false");
  expect(button("Color-blind mode").getAttribute("aria-pressed")).toBe("false");
});

it("is on while the page is in its mode", () => {
  html.theme = "dark";
  html.colors = "color-blind";
  render(
    <>
      {dark}
      {colorBlind}
    </>,
  );
  expect(button("Dark mode").getAttribute("aria-pressed")).toBe("true");
  expect(button("Color-blind mode").getAttribute("aria-pressed")).toBe("true");
});

it("switches dark mode on and off, and remembers it", () => {
  html.theme = "light";
  render(dark);
  fireEvent.click(button("Dark mode"));
  expect(html.theme).toBe("dark");
  expect(localStorage.getItem("undercover-theme")).toBe("dark");
  expect(button("Dark mode").getAttribute("aria-pressed")).toBe("true");
  fireEvent.click(button("Dark mode"));
  expect(html.theme).toBe("light");
  expect(localStorage.getItem("undercover-theme")).toBe("light");
});

it("switches color-blind mode under its own key, without touching dark mode", () => {
  html.theme = "dark";
  html.colors = "brand";
  render(
    <>
      {dark}
      {colorBlind}
    </>,
  );
  fireEvent.click(button("Color-blind mode"));
  expect(html.colors).toBe("color-blind");
  expect(localStorage.getItem("undercover-colors")).toBe("color-blind");
  expect(localStorage.getItem("undercover-theme")).toBeNull();
  expect(html.theme).toBe("dark");
  fireEvent.click(button("Color-blind mode"));
  expect(html.colors).toBe("brand");
  expect(localStorage.getItem("undercover-colors")).toBe("brand");
});

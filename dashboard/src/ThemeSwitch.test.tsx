import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it } from "vitest";
import { ThemeSwitch } from "./ThemeSwitch";

const root = document.documentElement;

beforeEach(() => {
  root.dataset.theme = "light";
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete root.dataset.theme;
});

const slider = () => screen.getByRole("switch", { name: "Dark mode" });

it("is a switch named Dark mode, off in light mode", () => {
  render(<ThemeSwitch />);
  expect(slider().getAttribute("aria-checked")).toBe("false");
});

it("starts on in dark mode", () => {
  root.dataset.theme = "dark";
  render(<ThemeSwitch />);
  expect(slider().getAttribute("aria-checked")).toBe("true");
});

it("flips the theme, saves the choice and flips back", () => {
  render(<ThemeSwitch />);
  fireEvent.click(slider());
  expect(slider().getAttribute("aria-checked")).toBe("true");
  expect(root.dataset.theme).toBe("dark");
  expect(localStorage.getItem("undercover-theme")).toBe("dark");
  fireEvent.click(slider());
  expect(slider().getAttribute("aria-checked")).toBe("false");
  expect(root.dataset.theme).toBe("light");
  expect(localStorage.getItem("undercover-theme")).toBe("light");
});

it("hides the dot from screen readers", () => {
  const { container } = render(<ThemeSwitch />);
  const dot = container.querySelector(".switch-dot");
  expect(dot?.getAttribute("aria-hidden")).toBe("true");
});

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ThemeSwitch } from "./ThemeSwitch";

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});

const button = () => screen.getByRole("button", { name: "Dark mode" });

it("is off while the page is light", () => {
  document.documentElement.dataset.theme = "light";
  render(<ThemeSwitch />);
  expect(button().getAttribute("aria-pressed")).toBe("false");
});

it("is on while the page is dark", () => {
  document.documentElement.dataset.theme = "dark";
  render(<ThemeSwitch />);
  expect(button().getAttribute("aria-pressed")).toBe("true");
});

it("switches to dark, remembers it, and switches back", () => {
  document.documentElement.dataset.theme = "light";
  render(<ThemeSwitch />);
  fireEvent.click(button());
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("undercover-theme")).toBe("dark");
  expect(button().getAttribute("aria-pressed")).toBe("true");
  fireEvent.click(button());
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(localStorage.getItem("undercover-theme")).toBe("light");
  expect(button().getAttribute("aria-pressed")).toBe("false");
});

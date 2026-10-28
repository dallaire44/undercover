import { useState } from "react";

const KEY = "undercover-theme";

/** A switch between light and dark. The mode is the data-theme on <html>. */
export function ThemeSwitch() {
  const [dark, setDark] = useState(
    () => document.documentElement.dataset.theme === "dark",
  );

  const toggle = () => {
    const mode = dark ? "light" : "dark";
    document.documentElement.dataset.theme = mode;
    localStorage.setItem(KEY, mode);
    setDark(!dark);
  };

  return (
    <button type="button" aria-pressed={dark} onClick={toggle}>
      Dark mode
    </button>
  );
}

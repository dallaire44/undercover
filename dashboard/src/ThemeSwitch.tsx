import { useState } from "react";

const KEY = "undercover-theme";

/** A slider for dark mode. The theme lives in `data-theme` on `<html>`. */
export function ThemeSwitch() {
  const [dark, setDark] = useState(
    document.documentElement.dataset.theme === "dark",
  );

  const flip = () => {
    const theme = dark ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(KEY, theme);
    setDark(!dark);
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      className="switch"
      onClick={flip}
    >
      Dark mode
      <span className="switch-track" aria-hidden="true">
        <span className="switch-dot" aria-hidden="true" />
      </span>
    </button>
  );
}

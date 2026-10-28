import { useState } from "react";

/**
 * A slider for one mode of the page: the dot is at the left when the mode is off
 * and at the right when it is on. The mode is an attribute on <html>, set
 * before the page draws, and the choice is remembered in the browser.
 */
export function ModeSwitch({
  label,
  attribute,
  on,
  off,
  storageKey,
}: Readonly<{
  label: string;
  attribute: "theme" | "colors";
  on: string;
  off: string;
  storageKey: string;
}>) {
  const [active, setActive] = useState(
    () => document.documentElement.dataset[attribute] === on,
  );

  const toggle = () => {
    const mode = active ? off : on;
    document.documentElement.dataset[attribute] = mode;
    localStorage.setItem(storageKey, mode);
    setActive(!active);
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      className="slider"
      onClick={toggle}
    >
      <span className="track" aria-hidden="true">
        <span className="dot" />
      </span>
      {label}
    </button>
  );
}

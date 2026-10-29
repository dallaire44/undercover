import { useState } from "react";

interface ModeSwitchProps {
  readonly label: string;
  readonly attribute: string;
  readonly on: string;
  readonly off: string;
  readonly storageKey: string;
}

/**
 * A slider for a mode. The mode lives in an attribute on `<html>`, so the CSS
 * answers to it, and the choice is saved in the browser.
 */
export function ModeSwitch({
  label,
  attribute,
  on,
  off,
  storageKey,
}: ModeSwitchProps) {
  const root = document.documentElement;
  const [checked, setChecked] = useState(root.getAttribute(attribute) === on);

  const flip = () => {
    const mode = checked ? off : on;
    root.setAttribute(attribute, mode);
    localStorage.setItem(storageKey, mode);
    setChecked(!checked);
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className="switch"
      onClick={flip}
    >
      {label}
      <span className="switch-track" aria-hidden="true">
        <span className="switch-dot" aria-hidden="true" />
      </span>
    </button>
  );
}

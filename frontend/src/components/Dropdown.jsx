import { useEffect, useRef, useState } from "react";
import { useClickOutside } from "../hooks/useClickOutside.js";
import { CheckIcon, ChevronDownIcon } from "./icons.jsx";

// Styled stand-in for <select>. `onChange` receives { target: { value } } so it drops into `set(field)` handlers.
export default function Dropdown({ value, onChange, options, label }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useClickOutside(ref, setOpen);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const selected = options.find((o) => o.value === value);
  return (
    <div className="dropdown" ref={ref}>
      <button
        type="button"
        className={"dropdown-trigger" + (open ? " dropdown-trigger--open" : "")}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label}
      >
        <span>{selected?.label ?? "Select..."}</span>
        <ChevronDownIcon />
      </button>
      {open && (
        <ul className="dropdown-panel" role="listbox">
          {options.map((o) => (
            <li key={o.value} role="option" aria-selected={o.value === value}>
              <button
                type="button"
                className={"dropdown-option" + (o.value === value ? " dropdown-option--selected" : "")}
                onClick={() => {
                  onChange({ target: { value: o.value } });
                  setOpen(false);
                }}
              >
                <span>{o.label}</span>
                {o.value === value && <CheckIcon />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

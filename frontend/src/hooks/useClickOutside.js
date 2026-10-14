import { useEffect } from "react";

// Closes a floating panel on an outside mousedown. `close` is a stable setState, called with `false`.
export function useClickOutside(ref, close) {
  useEffect(() => {
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) close(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [ref, close]);
}

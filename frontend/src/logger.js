// Reports frontend errors to the console and to the backend (/api/client-log).
const BASE = import.meta.env.VITE_API_URL || "";
const MAX_REPORTS = 5; // per page load: a render loop must not be able to flood the server
const seen = new Set();
let sent = 0;

const clip = (v, n) => (v == null ? undefined : String(v).slice(0, n));

export function reportError(kind, message, stack) {
  const msg = clip(message, 500) || "unknown error";
  console.error(JSON.stringify({ level: "error", kind, message: msg, stack: clip(stack, 2000) }));
  const key = `${kind}|${msg}`;
  if (seen.has(key) || sent >= MAX_REPORTS) return; // identical repeats and overflow stay local
  seen.add(key);
  sent += 1;
  try {
    fetch(`${BASE}/api/client-log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: clip(kind, 40), message: msg, stack: clip(stack, 2000), url: clip(window.location.href, 300) }),
      keepalive: true,
    }).catch(() => {}); // reporting must never throw or retry
  } catch {
    /* ignore */
  }
}

export function installGlobalHandlers() {
  window.addEventListener("error", (e) => reportError("uncaught-error", e.message, e.error?.stack));
  window.addEventListener("unhandledrejection", (e) =>
    reportError("unhandled-rejection", e.reason?.message || String(e.reason), e.reason?.stack),
  );
}

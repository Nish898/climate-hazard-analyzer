import { reportError } from "./logger.js";

const BASE = import.meta.env.VITE_API_URL || "";

function qs(p) {
  const q = new URLSearchParams({ lat: p.lat, lon: p.lon, start: p.start, end: p.end, hazard: p.hazard });
  if (p.box && p.lat2 !== "" && p.lon2 !== "") {
    q.set("lat2", p.lat2);
    q.set("lon2", p.lon2);
  }
  return q.toString();
}

const STATUS_MESSAGES = {
  429: "Too many requests - please wait a minute and retry.",
  502: "The weather data provider is unavailable - try again shortly.",
  503: "The service is temporarily unavailable - try again shortly.",
  504: "The request timed out - try again; repeat requests are usually faster once data is cached.",
};

async function getJson(url, signal) {
  let r;
  try {
    r = await fetch(url, { signal });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    reportError("network-error", `${url.split("?")[0]}: ${e.message}`);
    throw new Error("Cannot reach the server - check your connection and try again.");
  }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status >= 500) reportError("api-error", `${url.split("?")[0]} -> ${r.status}`); // 4xx are user input problems
    const detail = typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : "";
    throw new Error(detail || STATUS_MESSAGES[r.status] || `Request failed (${r.status})`);
  }
  return body;
}

export const analyze = (p, signal) => getJson(`${BASE}/api/analyze?${qs(p)}`, signal);
export const searchPlaces = (q, signal) => getJson(`${BASE}/api/geocode?q=${encodeURIComponent(q)}`, signal);
export const csvUrl = (p) => `${BASE}/api/export.csv?${qs(p)}`;

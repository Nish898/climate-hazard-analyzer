import { useEffect, useRef, useState } from "react";
import { searchPlaces } from "../api.js";
import Dropdown from "./Dropdown.jsx";
import { SearchIcon } from "./icons.jsx";
import ToggleSwitch from "./ToggleSwitch.jsx";

const HAZARDS = [{ value: "heatwave", label: "Heatwave" }];

export default function Controls({ form, setForm, onSubmit, loading, maxYear }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const skipSearch = useRef(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  // Debounced place search.
  useEffect(() => {
    if (skipSearch.current) {
      skipSearch.current = false;
      return undefined;
    }
    if (q.trim().length < 2) return setResults([]);
    const ctl = new AbortController(); // cancel stale searches so a slow old response can't overwrite a newer one
    const t = setTimeout(
      () => searchPlaces(q.trim(), ctl.signal).then((r) => setResults(r.results)).catch((e) => e.name !== "AbortError" && setResults([])),
      350,
    );
    return () => {
      clearTimeout(t);
      ctl.abort();
    };
  }, [q]);

  const pick = (r) => {
    setForm({ ...form, lat: r.lat.toFixed(3), lon: r.lon.toFixed(3), place: [r.name, r.admin1, r.country].filter(Boolean).join(", ") });
    skipSearch.current = true; // the name we put in the box shouldn't trigger a new search
    setResults([]);
    setQ([r.name, r.admin1, r.country].filter(Boolean).join(", "));
  };

  return (
    <form
      className="card controls"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <label className="field field-full">
        <span>Search city / region</span>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Delhi, Phoenix, Madrid" maxLength={80} />
        {results.length > 0 && (
          <ul className="suggest">
            {results.map((r, i) => (
              <li key={`${r.lat},${r.lon},${i}`} onClick={() => pick(r)}>
                {[r.name, r.admin1, r.country].filter(Boolean).join(", ")}
              </li>
            ))}
          </ul>
        )}
      </label>

      <div className="field">
        <span>Hazard</span>
        <Dropdown value={form.hazard} onChange={set("hazard")} options={HAZARDS} label="Hazard" />
      </div>
      <div className="controls-toggle">
        <ToggleSwitch checked={form.box} onChange={(e) => setForm({ ...form, box: e.target.checked })} label="Lat/lon box" />
      </div>

      <label className="field">
        <span>Latitude</span>
        <input type="number" step="any" min="-90" max="90" value={form.lat} onChange={set("lat")} required />
      </label>
      <label className="field">
        <span>Longitude</span>
        <input type="number" step="any" min="-180" max="180" value={form.lon} onChange={set("lon")} required />
      </label>
      {form.box && (
        <>
          <label className="field">
            <span>Corner 2 lat</span>
            <input type="number" step="any" min="-90" max="90" value={form.lat2} onChange={set("lat2")} required />
          </label>
          <label className="field">
            <span>Corner 2 lon</span>
            <input type="number" step="any" min="-180" max="180" value={form.lon2} onChange={set("lon2")} required />
          </label>
        </>
      )}

      <label className="field">
        <span>From year</span>
        <input type="number" min="1950" max={maxYear} value={form.start} onChange={set("start")} required />
      </label>
      <label className="field">
        <span>To year</span>
        <input type="number" min="1950" max={maxYear} value={form.end} onChange={set("end")} required />
      </label>

      <button type="submit" className="btn btn--primary" disabled={loading}>
        <SearchIcon />
        {loading ? "Analyzing..." : "Analyze"}
      </button>
    </form>
  );
}

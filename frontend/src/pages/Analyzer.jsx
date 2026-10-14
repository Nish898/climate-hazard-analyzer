import { useEffect, useRef, useState } from "react";
import { analyze, csvUrl } from "../api.js";
import Charts from "../components/Charts.jsx";
import Controls from "../components/Controls.jsx";
import { AlertIcon, PinIcon } from "../components/icons.jsx";
import InsightPanel from "../components/InsightPanel.jsx";
import MapPicker from "../components/MapPicker.jsx";
import "./Analyzer.css";

const MAX_YEAR = new Date().getFullYear() - 1;
const INITIAL = { lat: "28.614", lon: "77.209", lat2: "", lon2: "", box: false, start: 1990, end: 2020, hazard: "heatwave", place: "New Delhi, India" };

function Hero({ shown, data, loading }) {
  return (
    <section className="hero">
      <span className="hero-blob hero-blob--one" />
      <span className="hero-blob hero-blob--two" />
      <div className="hero-content">
        {shown && data ? (
          <>
            <h2>{shown.place}</h2>
            <div className="hero-sub">
              <span className="hero-pill">
                <PinIcon /> {data.location.lat}, {data.location.lon}
              </span>
              <span className="hero-pill">
                {data.range.start}&ndash;{data.range.end}
              </span>
              <span className="hero-pill">{data.quality.pct_valid}% valid days</span>
              <span className="hero-pill">{data.meta.cached ? "Served from cache" : "Freshly computed"}</span>
            </div>
          </>
        ) : (
          <>
            <h2>Heatwave trends, anywhere on Earth</h2>
            <p>{loading ? "Fetching and analysing decades of daily data..." : "Search for a place or click the map, then press Analyze."}</p>
          </>
        )}
      </div>
    </section>
  );
}

export default function Analyzer() {
  const [form, setForm] = useState(INITIAL);
  // `shown` is the form that produced `data`, so the title and CSV link stay in sync while the form is edited
  const [shown, setShown] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inflight = useRef(null);

  const run = async (f = form) => {
    inflight.current?.abort();
    const ctl = new AbortController();
    inflight.current = ctl;
    setLoading(true);
    setError("");
    try {
      const result = await analyze(f, ctl.signal);
      setData(result);
      setShown(f);
    } catch (e) {
      if (e.name === "AbortError") return;
      setError(e.message);
    } finally {
      if (inflight.current === ctl) setLoading(false);
    }
  };
  useEffect(() => {
    run();
    return () => inflight.current?.abort();
  }, []); // eslint-disable-line

  // In box mode the first click sets corner 1, the next sets corner 2, alternating.
  const [corner, setCorner] = useState(1);
  const onPick = (lat, lon) => {
    if (form.box && corner === 2) {
      setForm({ ...form, lat2: lat, lon2: lon });
      setCorner(1);
    } else {
      setForm({ ...form, lat, lon, place: "Custom point", ...(form.box ? { lat2: "", lon2: "" } : {}) });
      if (form.box) setCorner(2);
    }
  };

  return (
    <div className="analyzer">
      <Hero shown={shown} data={data} loading={loading} />

      <div className="analyzer-grid">
        <aside className="analyzer-side">
          <Controls form={form} setForm={setForm} onSubmit={() => run()} loading={loading} maxYear={MAX_YEAR} />
          <div className="card map-card">
            <h3>Location</h3>
            <MapPicker form={form} onPick={onPick} />
            <p className="small muted">
              {form.box ? `Click the map to set corner ${corner} of the box.` : "Click the map to move the point."} Box analyses use the box centre.
            </p>
          </div>
        </aside>

        <div className="analyzer-main">
          {error && (
            <div className="state state--error" role="alert">
              <AlertIcon /> {error}
            </div>
          )}
          {loading && !data && (
            <div className="state">
              <span className="state-spinner" /> Fetching and analysing decades of daily data...
            </div>
          )}
          {data && shown && (
            <div className={"results" + (loading ? " dim" : "")}>
              <InsightPanel data={data} csvHref={csvUrl(shown)} />
              <Charts data={data} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

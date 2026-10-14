import { memo } from "react";
import { DownloadIcon, FlameIcon, SigmaIcon, ThermometerIcon, TrendIcon } from "./icons.jsx";

const fmt = (v, d = 2) => (v == null ? "-" : Number(v).toFixed(d));

function Stat({ Icon, value, label }) {
  return (
    <div className="card stat">
      <span className="stat-icon">
        <Icon />
      </span>
      <div>
        <b className="stat-value">{value}</b>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  );
}

function InsightPanel({ data, csvHref }) {
  const { insight, trends, quality, definition, top_events } = data;
  const mk = trends.heatwave_days.mann_kendall;
  const pValue = mk.p_value == null ? "-" : mk.p_value < 0.001 ? "<0.001" : fmt(mk.p_value, 3);

  return (
    <>
      <div className={`card insight ${insight.significant ? "sig" : ""}`}>
        <h2>{insight.headline}</h2>
        <ul className="caveats">
          {insight.caveats.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
        <div className="insight-actions">
          <a className="btn btn--primary" href={csvHref}>
            <DownloadIcon /> Download CSV
          </a>
        </div>
      </div>

      <div className="stats">
        <Stat Icon={FlameIcon} value={data.total_events} label="heatwave events" />
        <Stat Icon={TrendIcon} value={fmt(trends.heatwave_days.regression.slope)} label="days/yr slope (OLS)" />
        <Stat Icon={ThermometerIcon} value={fmt(mk.sen_slope)} label="Sen's slope, days/yr" />
        <Stat Icon={SigmaIcon} value={pValue} label="Mann-Kendall p-value" />
      </div>

      <div className="two">
        <div className="card">
          <h3>Longest events</h3>
          {top_events.length === 0 ? (
            <p className="small muted">No heatwave events in this period.</p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Start</th>
                    <th>Days</th>
                    <th>Peak Tmax</th>
                    <th>Peak excess</th>
                  </tr>
                </thead>
                <tbody>
                  {top_events.map((e) => (
                    <tr key={e.start}>
                      <td>{e.start}</td>
                      <td>
                        <span className="badge">{e.duration} d</span>
                      </td>
                      <td>{e.peak_tmax_c}&deg;C</td>
                      <td>
                        <span className="badge badge--deep">+{e.peak_excess_c}&deg;C</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="card">
          <h3>Method &amp; data quality</h3>
          <p className="small">
            Heatwave = {definition.min_consecutive_days}+ consecutive days with Tmax above the {definition.percentile}th percentile of that calendar day (&plusmn;
            {definition.window_days}-day window), baseline {definition.baseline[0]}&ndash;{definition.baseline[1]}.
          </p>
          <p className="small">
            {quality.pct_valid}% valid days &middot; {quality.missing_raw} missing &middot; {quality.out_of_range} out-of-range &middot; {quality.spikes_removed}{" "}
            spikes removed &middot; {quality.interpolated} gaps interpolated (&le;3 days).
          </p>
        </div>
      </div>
    </>
  );
}

export default memo(InsightPanel);

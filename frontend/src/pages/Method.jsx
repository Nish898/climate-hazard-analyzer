import "./Analyzer.css";

export default function Method() {
  return (
    <div className="info-page">
      <p className="lead">How a heatwave is defined, how the raw data is cleaned, and how the trend statistics are computed.</p>

      <div className="card">
        <h3>Heatwave definition</h3>
        <div className="def-grid">
          <div className="def-item">
            <b>95th</b>
            <span>percentile threshold per calendar day</span>
          </div>
          <div className="def-item">
            <b>3+ days</b>
            <span>consecutive days above it</span>
          </div>
          <div className="def-item">
            <b>&plusmn;7 days</b>
            <span>window around each calendar day</span>
          </div>
          <div className="def-item">
            <b>1991&ndash;2020</b>
            <span>baseline (WMO climate normal)</span>
          </div>
        </div>
        <p>
          A heatwave is a run of at least three consecutive days whose daily maximum temperature exceeds the 95th percentile of that calendar day, computed over the
          baseline period with a seven-day window either side so the threshold is smooth and has enough samples. A day with missing data breaks a run.
        </p>
      </div>

      <div className="card">
        <h3>Data cleaning</h3>
        <ul>
          <li>Values outside -90 to 60 &deg;C are treated as impossible and removed.</li>
          <li>A value that jumps more than 15 &deg;C away from both neighbours is treated as a glitch and removed.</li>
          <li>Gaps of up to 3 days are interpolated; longer gaps are left missing rather than invented.</li>
          <li>Years with less than 80% valid data are drawn grey and excluded from trend statistics.</li>
        </ul>
      </div>

      <div className="card">
        <h3>Trend statistics</h3>
        <p>
          Each metric gets an ordinary least-squares regression and a Mann-Kendall test with Sen&apos;s slope. Mann-Kendall is non-parametric, so it does not assume the
          yearly counts are normally distributed. The headline only calls a trend significant when p &lt; 0.05, and says nothing about a trend when fewer than ten years
          of usable data are available.
        </p>
      </div>
    </div>
  );
}

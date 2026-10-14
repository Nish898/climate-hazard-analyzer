import {
  Chart as ChartJS, CategoryScale, LinearScale, BarController, LineController, BarElement, LineElement, PointElement, Filler, Tooltip, Legend,
} from "chart.js";
import { memo } from "react";
import { Chart } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarController, LineController, BarElement, LineElement, PointElement, Filler, Tooltip, Legend);
ChartJS.defaults.font.family = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

// <canvas> cannot use CSS variables, so the palette is read from the theme tokens.
function palette() {
  const css = getComputedStyle(document.documentElement);
  const v = (name) => css.getPropertyValue(name).trim();
  return {
    warm: v("--color-accent-warm"),
    accent: v("--color-accent"),
    deep: v("--color-accent-deep"),
    trend: v("--color-heading"),
    grey: v("--color-text-faint-2"),
    text: v("--color-text-muted"),
    grid: v("--color-border-soft"),
    surface: v("--color-surface"),
  };
}

const rgba = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

// memo: the parent re-renders on every keystroke, the charts only depend on `data`
function Charts({ data }) {
  const c = palette();
  const rows = data.yearly;
  const labels = rows.map((r) => r.year);
  const reg = data.trends.heatwave_days.regression;
  const trendLine = reg.slope == null ? [] : rows.map((r) => +(reg.intercept + reg.slope * r.year).toFixed(2));
  // Years with poor data coverage are drawn grey so they aren't mistaken for real zeros.
  const barColors = rows.map((r) => (r.reliable ? c.warm : c.grey));

  const axis = (text) => ({
    title: { display: true, text, color: c.text },
    beginAtZero: true,
    ticks: { color: c.text },
    grid: { color: c.grid },
    border: { display: false },
  });
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom", labels: { color: c.text, usePointStyle: true, boxWidth: 8 } },
      tooltip: { backgroundColor: c.trend, titleColor: c.surface, bodyColor: c.surface, cornerRadius: 8, padding: 10 },
    },
  };
  const xAxis = { ticks: { color: c.text, maxRotation: 0, autoSkipPadding: 12 }, grid: { display: false }, border: { color: c.grid } };

  return (
    <div className="charts">
      <div className="card chart">
        <h3>Heatwave days per year</h3>
        <div className="chart-body">
          <Chart
            type="bar"
            options={{ ...base, scales: { x: xAxis, y: axis("days") } }}
            data={{
              labels,
              datasets: [
                { type: "bar", label: "Heatwave days", data: rows.map((r) => r.heatwave_days), backgroundColor: barColors, borderRadius: 4 },
                { type: "line", label: "5-yr rolling mean", data: rows.map((r) => r.days_rolling5), borderColor: c.accent, pointRadius: 0, borderWidth: 2.5 },
                { type: "line", label: "Linear trend", data: trendLine, borderColor: c.trend, borderDash: [6, 4], pointRadius: 0, borderWidth: 2 },
              ],
            }}
          />
        </div>
      </div>

      <div className="card chart">
        <h3>Frequency &amp; duration</h3>
        <div className="chart-body">
          <Chart
            type="bar"
            options={{
              ...base,
              scales: { x: xAxis, y: axis("events / year"), y1: { ...axis("mean days / event"), position: "right", grid: { drawOnChartArea: false } } },
            }}
            data={{
              labels,
              datasets: [
                { type: "bar", label: "Events", data: rows.map((r) => r.events), backgroundColor: c.warm, borderRadius: 4, yAxisID: "y" },
                { type: "line", label: "Mean duration", data: rows.map((r) => r.mean_duration), borderColor: c.deep, backgroundColor: c.deep, yAxisID: "y1", tension: 0.25, pointRadius: 2 },
              ],
            }}
          />
        </div>
      </div>

      <div className="card chart">
        <h3>Peak intensity (&deg;C above daily 95th percentile)</h3>
        <div className="chart-body">
          <Chart
            type="line"
            options={{ ...base, scales: { x: xAxis, y: axis("°C above threshold") } }}
            data={{
              labels,
              datasets: [
                { label: "Max excess", data: rows.map((r) => r.max_intensity_c), borderColor: c.accent, backgroundColor: rgba(c.accent, 0.15), fill: true, tension: 0.25, pointRadius: 2 },
              ],
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default memo(Charts);

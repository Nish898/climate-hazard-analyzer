import "./Analyzer.css";

export default function About() {
  return (
    <div className="info-page">
      <p className="lead">Historical heatwave frequency, duration and intensity for any point on Earth.</p>

      <div className="card">
        <h3>Data source</h3>
        <p>
          Daily maximum temperatures come from the ERA5 reanalysis, served by the Open-Meteo archive API. It needs no API key, covers the globe and reaches back to
          1950. ERA5 is a gridded model product (roughly 25 km), not weather-station records.
        </p>
      </div>

      <div className="card">
        <h3>What to keep in mind</h3>
        <ul>
          <li>A city is analysed at its geocoded point. A lat/lon box (up to 5&deg; per side) is analysed at its centre point, not as an area average.</li>
          <li>The grid smooths local extremes and urban heat, so values can differ from a nearby station.</li>
          <li>Humidity and night-time temperatures are ignored, though both matter for health impact.</li>
          <li>The end year must be a completed year; early in January the previous year may not be fully available yet.</li>
          <li>Heatwave counts are noisy from year to year, so short ranges can mislead.</li>
        </ul>
      </div>

      <div className="card">
        <h3>Exports and reproducibility</h3>
        <p>Every analysis can be downloaded as a CSV of the yearly metrics. Results are cached, and the page tells you whether an analysis was freshly computed or served from cache.</p>
      </div>
    </div>
  );
}

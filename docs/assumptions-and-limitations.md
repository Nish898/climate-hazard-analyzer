# Assumptions, limitations, improvements

## Assumptions

- **Data source**: Open-Meteo archive (ERA5 reanalysis). Chosen for no API key and global coverage. The archive reaches
  back to 1940; the app starts at 1950 to keep the cleaned series and baseline comparisons reliable.
- **Regions**: Open-Meteo is point-based. A city (or a place found by search) is its geocoded point; a lat/lon box
  (max 5 degrees per side) is analysed at its **centre point**. It is not an area average.
- **Baseline**: 1991-2020 fixed, the WMO standard climate normal.
- **Event year**: a heatwave spanning a year boundary counts in the year it starts.
- **Complete years only**: the end year cannot be the current (incomplete) year. Until 10 January the previous year is
  also excluded, because the ERA5 archive lags real time by a few days.
- **Heatwave definition**: percentile-based (3+ days above the 95th percentile of that calendar day). It is not an
  impact-based definition (e.g. IMD or heat-index thresholds).
- **Units**: temperatures are requested in degrees Celsius explicitly, so no unit conversion is needed.

## Limitations

- ERA5 is a ~25 km grid, so it smooths local extremes and urban heat; it is not station data.
- Baseline years overlap the analysis period, so early years can be slightly under-represented. This is standard practice but worth knowing.
- Humidity and night-time temperatures are ignored, though both matter for health impact.
- Only heatwaves are implemented. The service structure (`hazard` parameter, `ANALYSIS_VERSION`) allows
  adding droughts or heavy rainfall.
- A box that crosses the antimeridian (longitude +/-180) is rejected: the 5-degree check sees it as ~340 degrees wide.
- The rate limiter is per process, so multiple instances would need a shared store such as Redis.
- CSV export contains the yearly metrics only, not the insight text. There is no PDF export.
- The frontend has no automated tests (the backend has 100% line and branch coverage; see [testing.md](testing.md)).
- Nothing has been deployed from this repo yet; deployment steps are in [deployment.md](deployment.md).

## What I would improve with more time

- Area-averaged boxes (sample a grid of points) instead of centre-point analysis.
- Drought (SPI) and heavy-rainfall (R95p) hazards.
- Compare against station data (NOAA GHCN) to validate reanalysis.
- Redis for shared rate limits and caching; background pre-warming for popular cities.
- PDF export of the insight and charts; frontend tests; CI that runs pytest and the build.

## AI tools used

Claude Code (Anthropic) was used throughout: architecture, backend, frontend, tests, Docker, logging, bug-hunting and
docs. The output was checked with the test suite (100% line and branch coverage), a fuzz run over the analysis code, live
Open-Meteo calls and manual checks in a browser.

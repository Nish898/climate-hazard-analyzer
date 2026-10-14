# Climate Hazard Trend Analyzer

Pick a place and a time range; the app shows how **heatwaves** have changed there (frequency, duration,
intensity), with trend statistics and a plain-language insight that only claims what the data supports.

**Stack:** React + Vite + Chart.js + Leaflet · FastAPI + pandas/numpy · MongoDB · Open-Meteo (ERA5) data

## Run it

```powershell
copy .env.example .env             # settings and secrets live here (git-ignored)
docker compose up -d --build       # app: http://localhost:3000   API docs: http://localhost:8000/docs
```

Local development without Docker: [docs/running.md](docs/running.md).

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
```

## How it works

```
Browser --> nginx --> FastAPI --> Open-Meteo archive (only on a cache miss)
                         |
                         +--> MongoDB: raw daily series + computed analyses (cached, TTL)
```

1. Fetch daily max temperature (1991-2020 baseline plus the chosen range), clean it (gaps, impossible values, spikes).
2. **Heatwave** = 3+ consecutive days above the 95th percentile of that calendar day (+/-7-day window, 1991-2020 baseline).
3. Aggregate per year; fit OLS regression and Mann-Kendall + Sen's slope; build the insight.
4. A percent change is quoted only if the trend is statistically significant; otherwise the app says so.

Also: Leaflet map selection, CSV export, rate limiting, input validation, structured JSON logs with automatic
retention (`LOG_RETENTION_DAYS`), light-theme UI.

## Assumptions and limits

- Data is ERA5 reanalysis (~25 km grid), not station records. Years with <80% valid data are excluded from trends.
- A city is its geocoded point; a lat/lon box (max 5 degrees per side) is analysed at its **centre point**.
- Heatwaves only; the `hazard` parameter and cache versioning leave room for droughts and heavy rain.

## With more time

Area-averaged boxes, drought and heavy-rainfall hazards, validation against station data (NOAA GHCN),
PDF export, shared rate limiting/caching (Redis), frontend tests and CI.

## AI tools used

Claude Code (Anthropic) was used throughout: architecture, backend, frontend, tests, Docker, logging, bug-hunting and
docs. The output was checked with the test suite (100% line and branch coverage), a fuzz run over the analysis code, live
Open-Meteo calls and manual checks in a browser.

## Documentation

[docs/](docs/README.md): running · architecture · hazard logic · API · logging and settings · frontend · testing ·
deployment · assumptions.

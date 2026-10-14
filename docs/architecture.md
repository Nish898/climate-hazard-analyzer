# Architecture

```
Browser (React + Chart.js + Leaflet; pages: Analyzer, Method, About)
        |  /api/*
        v
 nginx (Docker) / Vite proxy (dev)
        |
        v
 FastAPI  --------------------------->  Open-Meteo archive + geocoding (ERA5)
   | validate -> rate-limit -> service            ^
   |                                              | only on cache miss
   v                                              |
 MongoDB: analyses (computed results)  <----------+
          raw_series (daily Tmax per point)
```

## Backend modules (`backend/app/`)

| Module | Responsibility |
|---|---|
| `main.py` | Routes, CORS, rate limiting, request logging, error handlers (no stack traces leak to clients) |
| `logging_config.py` | JSON logging, credential masking, daily rotation, size cap and automatic deletion of old logs |
| `schemas.py` | Validation of every user input (bounds, year range, box size, hazard allow-list) |
| `service.py` | Orchestration: analysis cache, then raw cache, then fetch, clean, detect, trend, store |
| `openmeteo.py` | HTTP client: fixed hosts, timeouts, retry with backoff |
| `cleaning.py` | Gap filling, range and spike checks, quality report |
| `heatwave.py` | Percentile thresholds, event detection, per-year metrics |
| `trends.py` | OLS regression, Mann-Kendall + Sen's slope, rolling mean |
| `insights.py` | Conservative plain-language summary |
| `db.py` | Mongo connection, TTL indexes, in-memory fallback |

## Frontend (`frontend/src/`)

Single-page React app with a sidebar/top-bar shell, three pages, and a token-based light theme. Charts read colours from the
theme tokens; frontend errors are reported to `POST /api/client-log` so they land in the same logs. Details in
[frontend.md](frontend.md).

## Request flow (`GET /api/analyze`)

1. Validate params (422 on failure), then apply the rate limit (429).
2. Look up `analyses` by key `hazard|lat,lon|start-end|vN`. Hit: return, `meta.cached=true`.
3. Miss: load daily Tmax from `raw_series` (refetching from Open-Meteo only if the cached range does not
   cover the baseline plus selected range).
4. Clean, compute thresholds, detect events, aggregate per year, fit trends, build insight.
5. Store in `analyses`, return JSON.

## Database (NoSQL, MongoDB)

| Collection | `_id` | Contents |
|---|---|---|
| `raw_series` | `"lat,lon"` (2 dp) | `dates[]`, `temps[]`, `start_year`, `end_year`, `fetched_at` |
| `analyses` | `hazard\|lat,lon\|start-end\|vN` | full result JSON, `fetched_at` |

Both have a TTL index on `fetched_at` (default 30 days). Raw data is shared across different year ranges for the
same point, so changing the range reuses it when it is already covered.

## Security and performance

- **Input safety**: all parameters are typed and bounds-checked; hazard is an allow-list; no user input is
  interpolated into URLs or queries (httpx `params`, parameterised Mongo lookups on derived keys).
- **Rate limiting**: `slowapi`, 60/min default (applied to every route except health checks) and 15/min on analysis endpoints, per client IP. nginx overwrites `X-Forwarded-For`, so clients cannot spoof it.
- **CORS**: allow-list from `CORS_ORIGINS`; GET plus the POST used by `/api/client-log`. Error responses carry CORS headers too.
- **Resilience**: a database outage degrades to uncached answers (logged, visible at `/api/ready`) instead of failing requests; client errors from the weather API are not retried.
- **Network exposure**: in Docker, MongoDB and the backend are bound to `127.0.0.1`; only the frontend port is public.
- **Observability**: structured logs with a per-request ID (see [logging.md](logging.md)).
- **Upstream safety**: fixed hosts, 30 s timeout, 3 retries with exponential backoff, 502 mapping.
- **Errors**: generic messages to clients, details in server logs.
- **Container**: backend runs as a non-root user.
- **Caching**: two layers (results, raw series); coordinates rounded to 2 dp so nearby clicks share cache entries.

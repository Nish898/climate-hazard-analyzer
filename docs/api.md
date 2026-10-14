# API reference

Interactive docs at `/docs` (Swagger UI) when the backend is running.

## `GET /api/analyze`

| Param | Required | Notes |
|---|---|---|
| `lat`, `lon` | yes | -90..90, -180..180 |
| `lat2`, `lon2` | no | Opposite box corner (both or neither). Box max 5 degrees per side; centre is analysed |
| `start`, `end` | no | Default 1990-2020. 1950 <= start <= end <= last full year; span >= 10 years |
| `hazard` | no | `heatwave` (only value) |

```
GET /api/analyze?lat=28.61&lon=77.21&start=1990&end=2020
```

Response (abridged):

```json
{
  "location": {"lat": 28.61, "lon": 77.21, "box": false},
  "range": {"start": 1990, "end": 2020},
  "definition": {"percentile": 95, "min_consecutive_days": 3, "window_days": 7, "baseline": [1991, 2020]},
  "yearly": [{"year": 1990, "events": 3, "heatwave_days": 14, "mean_duration": 4.67, "max_duration": 6,
              "max_intensity_c": 3.8, "coverage": 1.0, "reliable": true, "days_rolling5": null}],
  "trends": {"heatwave_days": {"regression": {"slope": 0.1, "r2": 0.05, "p_value": 0.2},
                                "mann_kendall": {"trend": "no significant trend", "p_value": 0.16, "sen_slope": 0.1}}},
  "insight": {"headline": "...", "significant": false, "pct_change": null, "caveats": ["..."]},
  "top_events": [{"start": "...", "end": "...", "duration": 9, "peak_excess_c": 6.1, "peak_tmax_c": 46.2}],
  "quality": {"pct_valid": 100.0, "missing_raw": 0, "interpolated": 0},
  "meta": {"cached": false, "generated_at": "..."}
}
```

## `GET /api/export.csv`

Same parameters; returns the yearly metrics table as a CSV download.

## `GET /api/geocode?q=<text>`

Place search (2-80 chars) via Open-Meteo geocoding. Returns `{results: [{name, admin1, country, lat, lon}]}`.

## `POST /api/client-log`

Browser error reports (used by the frontend). JSON body: `kind` (max 40 chars), `message` (max 500),
optional `stack` (max 2000) and `url` (max 300). Returns 204. Limited to 10/min per IP.

## `GET /api/health` and `GET /api/ready`

`/api/health` is liveness: `{"status": "ok"}` whenever the process is up. `/api/ready` checks the database:
`{"status": "ok", "database": "up"}`, or 503 `{"status": "unavailable", "database": "down"}`. Neither is rate-limited.

Every response includes an `X-Request-ID` header that also appears in the server logs.

## Limits

Per client IP: 15 requests/min on `/api/analyze` and `/api/export.csv`, 10/min on `/api/client-log`, 60/min on every other
route except the health checks. Configurable in `.env` (see [logging.md](logging.md)).

## Errors

| Status | Meaning |
|---|---|
| 422 | Invalid input, or no temperature data for the location/period. `detail` is always a readable string, e.g. `lat: Input should be less than or equal to 90` |
| 429 | Rate limit exceeded |
| 502 | Upstream data provider unavailable |
| 500 | Unexpected error. The body has only a generic message and a `request_id`; details are in the server logs |

A failing database does not fail analysis requests: results are computed without the cache and the problem is
logged. Use `/api/ready` to detect it.

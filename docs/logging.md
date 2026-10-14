# Logging and configuration

## Where logs go

The backend writes **one JSON object per line** to stdout (`docker compose logs backend`) and to a daily-rotated
file, `app.log`, in `LOG_DIR` (in Docker: the `backend_logs` volume mounted at `/app/logs`).

```json
{"ts": "2026-10-13T09:52:16.680+00:00", "level": "INFO", "logger": "api", "message": "request completed",
 "request_id": "87a0c630444c", "method": "GET", "path": "/api/analyze", "client": "172.19.0.1",
 "status": 200, "duration_ms": 1160.3}
```

| Logger | What it records |
|---|---|
| `api` | Every request: method, path, status, duration, client IP. Failures log a traceback |
| `service` | Cache hits, data-quality summary, computed results, cache read/write failures |
| `openmeteo` | Each upstream call (status, latency, attempt), retries and final failure |
| `db` | Connection, fallback to in-memory store, index problems |
| `client` | Errors reported by the browser (see below) |

Every response carries an `X-Request-ID` header, and the same `request_id` appears on every log line written while
serving that request. A user can quote it from a failed response to find the matching log lines.

Credentials in URIs (`scheme://user:pass@host`) are masked as `***:***@` in messages and tracebacks. Do not put
secrets in `extra` fields or log them by other means.

## Retention (automatic deletion)

- The live file rotates at midnight UTC, or earlier if it exceeds `LOG_MAX_MB`.
- Rotated files (`app.log.YYYY-MM-DD`, `.1`, `.2`, ...) older than `LOG_RETENTION_DAYS` are deleted at every
  rotation and every time the backend starts. The live `app.log` is never deleted.
- To keep logs longer, raise `LOG_RETENTION_DAYS` in `.env` and run `docker compose up -d`.

## Settings (`.env`)

All configuration and any secrets live in `.env` (git-ignored, excluded from the Docker image). Copy
`.env.example` to start. Docker Compose passes the whole file to the backend.

| Variable | Default | Meaning |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Invalid values stop startup with a clear error |
| `LOG_TO_FILE` | `true` | `false` logs to stdout only |
| `LOG_DIR` | `logs` (`/app/logs` in Docker) | Log directory. If it is not writable the app keeps running with stdout logging |
| `LOG_RETENTION_DAYS` | `3` | Delete rotated logs older than this many days (minimum 1) |
| `LOG_MAX_MB` | `50` | Rotate the live file early past this size |
| `MONGO_URI`, `MONGO_DB` | | Database connection. Put credentials only here |
| `CORS_ORIGINS` | | Comma-separated allowed browser origins |
| `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_ANALYZE`, `RATE_LIMIT_CLIENT_LOG` | `60/minute`, `15/minute`, `10/minute` | Per-IP limits |
| `ALLOW_MONGOMOCK_FALLBACK` | `false` in Docker | `true` allows an in-memory store when Mongo is unreachable |

## Frontend errors

The browser reports uncaught errors, unhandled promise rejections, React render crashes and 5xx/network API
failures to `POST /api/client-log`, so they appear in the same logs under logger `client`. Safeguards: fields are
length-limited, the endpoint is rate-limited, and each page load sends at most 5 distinct reports.

## Reading logs

```powershell
docker compose logs backend --tail 50                 # recent lines
docker compose logs backend | Select-String '"level": "ERROR"'
docker compose exec backend ls -la /app/logs          # files and their sizes
```

# Running the app

Repo layout:

```
climate-hazard-analyzer/
  .venv/            Python virtual env (project root, git-ignored)
  .env              settings and secrets (git-ignored; copy from .env.example)
  backend/          FastAPI service, Dockerfile
  tests/            all backend test cases (pytest)
  frontend/         React + Vite app, Dockerfile, nginx.conf
  docs/             this documentation
  docker-compose.yml
  pytest.ini        test configuration (run pytest from here)
```

## Option A: Docker (everything, one command)

Requires Docker Desktop.

```powershell
docker compose up -d --build
```

- App: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- Stop: `docker compose down` (add `-v` to also wipe the cached data **and log** volumes)
- Settings and secrets: copy `.env.example` to `.env` (see [logging.md](logging.md) for every variable)
- MongoDB and the backend are published on `127.0.0.1` only (Mongo has no authentication); only port 3000 is
  reachable from other machines
- Check health: `docker compose ps` (mongo and backend show `healthy`), `http://localhost:3000/api/ready`
- After pulling frontend changes, hard-refresh the browser (Ctrl+Shift+R)

## Option B: Local development

Requires Python 3.10+ and Node 18+. MongoDB is optional: if none is reachable, the backend falls back to an
in-memory store (data is lost on restart). To use a real one, run `docker compose up -d mongo`.

### Backend

The virtual env lives at the **project root**, not inside `backend/`.

```powershell
# from the project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r backend\requirements-dev.txt   # runtime deps + pytest/pytest-cov

cd backend
copy .env.example .env                # optional; defaults work
uvicorn app.main:app --reload --port 8000
```

### Frontend

UI structure and conventions: [frontend.md](frontend.md).

```powershell
cd frontend
npm install
npm run dev                           # http://localhost:5173, proxies /api to :8000
```

## Tests

Run from the **project root** (`pytest.ini` points pytest at `tests/` and puts `backend/` on the import path):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Coverage report (with the lines each file misses):

```powershell
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
```

More detail (files, coverage): [testing.md](testing.md). Tests are offline (and write no log files): they stub the Open-Meteo call and use an in-memory database.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| First analysis takes ~5-10 s | Fetching 30+ years from Open-Meteo. Repeats are served from the database in milliseconds |
| `502 Weather data provider is unavailable` | Open-Meteo unreachable or rate-limiting; retry shortly |
| `429 Too many requests` | App rate limit (15 analyses/min/IP by default); see `RATE_LIMIT_ANALYZE` |
| Blank page or console errors after a rebuild | Hard-refresh (Ctrl+Shift+R) so the browser drops the old bundle. Frontend errors are also written to the backend logs (logger `client`) |
| Where are the logs? | `docker compose logs backend`, or the `/app/logs` volume. Files older than `LOG_RETENTION_DAYS` are deleted automatically |
| `422` with a message | Input validation, e.g. range under 10 years, years out of bounds, box over 5 degrees |
| Cached results look stale after changing hazard logic | Bump `ANALYSIS_VERSION` in `backend/app/service.py` |

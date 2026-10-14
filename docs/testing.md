# Testing

All tests live in `tests/` at the project root. `pytest.ini` points pytest at that folder and puts `backend/` on the
import path, so run everything from the project root.

| File | Covers |
|---|---|
| `conftest.py` | Shared setup: no log files written during tests, rate limiter reset between tests |
| `test_core.py` | Heatwave detection, thresholds, cleaning, Mann-Kendall, regression, API caching, input rejection, CSV export |
| `test_robustness.py` | Failure modes: empty or null upstream data, database outage, error responses (JSON 500 with CORS), rate limits, retry rules, log formatting and retention, client error reports |
| `test_coverage.py` | Remaining branches: database connection paths, insight wording variants, logging setup, upstream parsing, cache reuse, validation edges |

Tests are offline and deterministic: Open-Meteo is stubbed and the database is in-memory (mongomock).

## Run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Coverage

```powershell
.\.venv\Scripts\pip.exe install -r backend\requirements-dev.txt   # once (pytest + pytest-cov)
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=html     # browsable report in htmlcov\index.html
```

`.coveragerc` measures `backend/app` with branch coverage. At the time of writing the suite reaches 100% of lines and
branches. High coverage shows code was exercised, not that every behaviour is asserted: the frontend has no
automated tests, and database tests use a fake client rather than a live MongoDB.

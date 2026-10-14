"""Tests for branches the other suites do not reach: DB connection paths, insight wording, logging setup,
upstream parsing, error handlers and validation edges."""
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import mongomock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pymongo.errors import ServerSelectionTimeoutError

from app import db, heatwave, insights, logging_config, openmeteo, service, trends
from app.config import settings
from app.schemas import AnalyzeParams


# ---- db.py -------------------------------------------------------------------------------------


@pytest.fixture()
def fresh_db():
    """Start from 'not connected' and always leave a working in-memory db behind."""
    db._db, db._failed_at = None, 0.0
    yield
    db.set_db(mongomock.MongoClient()["test"])
    db._failed_at = 0.0


def _fake_client(fail: bool, built: list):
    class FakeClient:
        def __init__(self, *a, **k):
            built.append(1)
            self.admin = SimpleNamespace(command=self._ping)

        def _ping(self, _):
            if fail:
                raise ServerSelectionTimeoutError("no server")
            return {"ok": 1}

        def __getitem__(self, name):
            return mongomock.MongoClient()[name]

    return FakeClient


def test_get_db_connects_and_reuses_the_connection(fresh_db, monkeypatch):
    built = []
    monkeypatch.setattr(db, "MongoClient", _fake_client(False, built))
    first = db.get_db()
    assert db.get_db() is first and len(built) == 1


def test_get_db_falls_back_to_mongomock_when_allowed(fresh_db, monkeypatch):
    monkeypatch.setattr(db, "MongoClient", _fake_client(True, []))
    monkeypatch.setattr(settings, "allow_mongomock_fallback", True)
    assert "mongomock" in type(db.get_db().client).__module__  # a usable in-memory database


def test_get_db_fails_loudly_then_fast_when_fallback_disabled(fresh_db, monkeypatch):
    built = []
    monkeypatch.setattr(db, "MongoClient", _fake_client(True, built))
    monkeypatch.setattr(settings, "allow_mongomock_fallback", False)
    with pytest.raises(ServerSelectionTimeoutError):
        db.get_db()
    with pytest.raises(Exception, match="recent connection failure"):
        db.get_db()
    assert len(built) == 1  # the second call did not even try to connect


def test_get_db_returns_connection_made_by_another_thread_while_waiting(fresh_db, monkeypatch):
    class RacingLock:
        def __enter__(self):
            db._db = "made-by-other-thread"

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(db, "_lock", RacingLock())
    assert db.get_db() == "made-by-other-thread"


def test_ping_reports_up_and_down(fresh_db):
    db.set_db(mongomock.MongoClient()["t"])
    assert db.ping() is True

    class Down:
        def list_collection_names(self):
            raise ServerSelectionTimeoutError("down")

    db.set_db(Down())
    assert db.ping() is False


# ---- insights.py -------------------------------------------------------------------------------


def _years(n, days, reliable=True, start=2000):
    return [{"year": start + i, "heatwave_days": d, "reliable": reliable} for i, d in zip(range(n), days)]


def test_insight_too_few_usable_years_mentions_excluded():
    rows = _years(5, [1] * 5) + _years(3, [0] * 3, reliable=False, start=2005)
    out = insights.build_insight(rows, {"p_value": None}, {}, 2000, 2007)
    assert "Only 5 usable years" in out["headline"] and any("3 year(s)" in c for c in out["caveats"])
    assert out["significant"] is False and out["pct_change"] is None


def test_insight_significant_increase_with_percent():
    rows = _years(20, [2] * 10 + [6] * 10)
    mk = {"p_value": 0.001, "trend": "increasing", "sen_slope": 0.4}
    out = insights.build_insight(rows, mk, {}, 2000, 2019)
    assert out["significant"] and out["pct_change"] == 200.0
    assert "increased by about 200%" in out["headline"]


def test_insight_significant_decrease_wording():
    rows = _years(20, [8] * 10 + [4] * 10)
    mk = {"p_value": 0.01, "trend": "decreasing", "sen_slope": -0.3}
    assert "decreased by about 50%" in insights.build_insight(rows, mk, {}, 2000, 2019)["headline"]


def test_insight_significant_but_baseline_too_low_for_percent():
    rows = _years(20, [0] * 10 + [3] * 10)
    mk = {"p_value": 0.01, "trend": "increasing", "sen_slope": 0.2}
    out = insights.build_insight(rows, mk, {}, 2000, 2019)
    assert out["pct_change"] is None and "Sen's slope +0.20" in out["headline"]
    assert any("below 1 heatwave day" in c for c in out["caveats"])


def test_insight_not_significant_and_no_estimate():
    rows = _years(20, [3] * 20)
    assert "No statistically significant trend" in insights.build_insight(rows, {"p_value": 0.4}, {}, 2000, 2019)["headline"]
    assert "No trend could be estimated" in insights.build_insight(rows, {"p_value": None}, {}, 2000, 2019)["headline"]


# ---- logging_config.py -------------------------------------------------------------------------


@pytest.fixture()
def restore_logging():
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    uv = {n: (logging.getLogger(n).propagate, list(logging.getLogger(n).handlers)) for n in ("uvicorn", "uvicorn.error", "uvicorn.access")}
    yield root
    for h in root.handlers:
        if h not in saved[0]:
            h.close()
    root.handlers[:] = saved[0]
    root.setLevel(saved[1])
    for n, (prop, handlers) in uv.items():
        logging.getLogger(n).propagate, logging.getLogger(n).handlers[:] = prop, handlers


def test_formatter_includes_exception_traceback():
    try:
        raise ValueError("kaput at mongodb://u:pw@h/x")
    except ValueError:
        rec = logging.LogRecord("t", logging.ERROR, __file__, 1, "failed", None, logging.sys.exc_info())
    out = json.loads(logging_config.JsonFormatter().format(rec))
    assert "ValueError" in out["exception"] and "pw" not in out["exception"]


def test_request_id_is_included_when_set():
    token = logging_config.request_id_var.set("abc123")
    try:
        rec = logging.LogRecord("t", logging.INFO, __file__, 1, "m", None, None)
        assert json.loads(logging_config.JsonFormatter().format(rec))["request_id"] == "abc123"
    finally:
        logging_config.request_id_var.reset(token)


def test_purge_ignores_files_it_cannot_delete(tmp_path, monkeypatch):
    old = tmp_path / "app.log.2020-01-01"
    old.write_text("x")
    os.utime(old, (1, 1))

    def refuse(self, *a, **k):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "unlink", refuse)
    assert logging_config.purge_old_logs(tmp_path, 3) == 0  # no crash, nothing counted


def test_should_rollover_by_time_and_by_size(tmp_path):
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "m", None, None)
    handler = logging_config.RetentionFileHandler(tmp_path, 3, max_bytes=10**9)
    uncapped = logging_config.RetentionFileHandler(tmp_path / "b", 3, max_bytes=0) if (tmp_path / "b").mkdir() is None else None
    try:
        handler.emit(rec)
        assert handler.shouldRollover(rec) is False  # under the size cap, before midnight
        assert uncapped.shouldRollover(rec) is False  # no size cap configured
        handler.max_bytes = 1
        assert handler.shouldRollover(rec) is True  # over the size cap
        handler.max_bytes, handler.rolloverAt = 10**9, 0
        assert handler.shouldRollover(rec) is True  # past midnight
    finally:
        handler.close()
        uncapped.close()


def test_ttl_index_failure_is_logged_not_raised(caplog):
    class BadCollection:
        def create_index(self, *a, **k):
            raise RuntimeError("index options conflict")

    class BadDb(dict):
        def __missing__(self, key):
            return BadCollection()

    with caplog.at_level(logging.WARNING, logger="db"):
        db._ensure_indexes(BadDb())
    assert sum("Could not create TTL index" in r.getMessage() for r in caplog.records) == 2


def test_unique_name_skips_existing(tmp_path):
    base = str(tmp_path / "app.log.2026-01-01")
    assert logging_config.RetentionFileHandler._unique_name(base) == base
    Path(base).write_text("x")
    assert logging_config.RetentionFileHandler._unique_name(base).endswith(".1")
    Path(base + ".1").write_text("x")
    assert logging_config.RetentionFileHandler._unique_name(base).endswith(".2")


def test_setup_logging_writes_json_to_file(tmp_path, monkeypatch, restore_logging):
    monkeypatch.setattr(settings, "log_to_file", True)
    monkeypatch.setattr(settings, "log_dir", str(tmp_path / "logs"))
    monkeypatch.setattr(settings, "log_level", "INFO")
    old = tmp_path / "logs"
    old.mkdir()
    stale = old / "app.log.2020-01-01"
    stale.write_text("x")
    os.utime(stale, (1, 1))

    logging_config.setup_logging()
    logging.getLogger("probe").info("hello", extra={"k": "v"})
    for h in logging.getLogger().handlers:
        h.flush()
    lines = [json.loads(line) for line in (old / "app.log").read_text().splitlines()]
    assert any(line["message"] == "hello" and line["k"] == "v" for line in lines)
    assert any(line["message"] == "Logging initialised" and line["purged_files"] == 1 for line in lines)
    assert not stale.exists()


def test_setup_logging_survives_unwritable_directory(tmp_path, monkeypatch, restore_logging, capsys):
    blocker = tmp_path / "afile"
    blocker.write_text("not a directory")
    monkeypatch.setattr(settings, "log_to_file", True)
    monkeypatch.setattr(settings, "log_dir", str(blocker / "sub"))
    monkeypatch.setattr(settings, "log_level", "INFO")  # the suite pins CRITICAL, which would hide the warning
    logging_config.setup_logging()  # must not raise
    assert "File logging disabled" in capsys.readouterr().out
    assert all(not isinstance(h, logging_config.RetentionFileHandler) for h in logging.getLogger().handlers)


# ---- openmeteo.py ------------------------------------------------------------------------------


def test_fetch_daily_tmax_parses_and_validates(monkeypatch):
    monkeypatch.setattr(openmeteo, "_get", lambda url, params: {"daily": {"time": ["2000-01-01", "2000-01-02"], "temperature_2m_max": [20.5, None]}})
    assert openmeteo.fetch_daily_tmax(1, 2, 2000, 2000) == (["2000-01-01", "2000-01-02"], [20.5, None])
    for bad in ({}, {"daily": {"time": ["2000-01-01"], "temperature_2m_max": [1, 2]}}, {"daily": {"time": [], "temperature_2m_max": []}}):
        monkeypatch.setattr(openmeteo, "_get", lambda url, params, b=bad: b)
        with pytest.raises(openmeteo.UpstreamError):
            openmeteo.fetch_daily_tmax(1, 2, 2000, 2000)


def test_geocode_maps_results(monkeypatch):
    body = {"results": [{"name": "Paris", "admin1": "IdF", "country": "France", "latitude": 48.85, "longitude": 2.35}]}
    monkeypatch.setattr(openmeteo, "_get", lambda url, params: body)
    assert openmeteo.geocode("paris") == [{"name": "Paris", "admin1": "IdF", "country": "France", "lat": 48.85, "lon": 2.35}]
    monkeypatch.setattr(openmeteo, "_get", lambda url, params: {})
    assert openmeteo.geocode("nowhere") == []


def test_get_returns_json_on_success_and_retries_network_errors(monkeypatch):
    class Ok:
        status_code = 200

        def json(self):
            return {"ok": True}

    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: Ok())
    assert openmeteo._get("http://x", {}) == {"ok": True}

    calls = []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) < 3:
            raise openmeteo.httpx.ConnectError("boom")
        return Ok()

    monkeypatch.setattr(openmeteo.httpx, "get", flaky)
    monkeypatch.setattr(openmeteo.time, "sleep", lambda s: None)
    assert openmeteo._get("http://x", {}) == {"ok": True} and len(calls) == 3


# ---- service.py / main.py error paths ----------------------------------------------------------


@pytest.fixture()
def client():
    from app.main import app

    db.set_db(mongomock.MongoClient()["cov"])
    return TestClient(app, raise_server_exceptions=False)


def _tmax(years):
    idx = pd.DatetimeIndex([d for y in years for d in pd.date_range(f"{y}-01-01", f"{y}-12-31")])
    vals = 20 + 8 * np.sin((idx.dayofyear - 100) / 365 * 2 * np.pi) + np.random.default_rng(1).normal(0, 1, len(idx))
    return idx.strftime("%Y-%m-%d").tolist(), vals.round(1).tolist()


def test_upstream_failure_is_a_502(client, monkeypatch):
    def down(*a, **k):
        raise openmeteo.UpstreamError("provider down")

    monkeypatch.setattr(service, "fetch_daily_tmax", down)
    r = client.get("/api/analyze?lat=1&lon=1&start=1991&end=2020")
    assert r.status_code == 502 and "unavailable" in r.json()["detail"]


def test_empty_upstream_series_is_a_422(client, monkeypatch):
    monkeypatch.setattr(service, "fetch_daily_tmax", lambda *a: ([], []))
    r = client.get("/api/analyze?lat=2&lon=2&start=1991&end=2020")
    assert r.status_code == 422 and "Empty" in r.json()["detail"]


def test_no_data_in_baseline_period_is_a_422(client, monkeypatch):
    first_year = settings.baseline_end + 1  # data exists, but only after the baseline window
    monkeypatch.setattr(service, "fetch_daily_tmax", lambda *a: _tmax(range(first_year, first_year + 3)))
    r = client.get(f"/api/analyze?lat=3&lon=3&start=2000&end={first_year + 3}")
    assert r.status_code == 422 and "baseline" in r.json()["detail"]


def test_raw_series_cache_is_reused_for_a_narrower_range(client, monkeypatch):
    calls = []

    def fetch(lat, lon, s, e):
        calls.append((s, e))
        return _tmax(range(s, e + 1))

    monkeypatch.setattr(service, "fetch_daily_tmax", fetch)
    assert client.get("/api/analyze?lat=4&lon=4&start=1991&end=2020").status_code == 200
    r = client.get("/api/analyze?lat=4&lon=4&start=1995&end=2015")  # new analysis key, raw data already covered
    assert r.status_code == 200 and r.json()["meta"]["cached"] is False and len(calls) == 1


def test_raw_series_cache_is_extended_for_a_wider_range(client, monkeypatch):
    calls = []

    def fetch(lat, lon, s, e):
        calls.append((s, e))
        return _tmax(range(s, e + 1))

    monkeypatch.setattr(service, "fetch_daily_tmax", fetch)
    client.get("/api/analyze?lat=5&lon=5&start=1991&end=2020")
    client.get("/api/analyze?lat=5&lon=5&start=1960&end=2000")
    assert calls[1] == (1960, 2020)  # refetched as the union of cached and requested years


def test_cache_write_failure_is_swallowed(monkeypatch):
    class BrokenCollection:
        def replace_one(self, *a, **k):
            raise ServerSelectionTimeoutError("down")

    class BrokenDb:
        def __getitem__(self, _):
            return BrokenCollection()

    db.set_db(BrokenDb())
    service._cache_put("analyses", {"_id": "k"})  # logs, does not raise
    db.set_db(mongomock.MongoClient()["cov"])


# ---- schemas.py, trends.py, heatwave.py edges --------------------------------------------------


def test_box_parameters_validated_and_centred():
    with pytest.raises(ValidationError, match="both lat2 and lon2"):
        AnalyzeParams(lat=1, lon=1, lat2=2, start=1991, end=2020)
    with pytest.raises(ValidationError, match="Years must satisfy"):
        AnalyzeParams(lat=1, lon=1, start=2020, end=1991)
    with pytest.raises(ValidationError, match="at least 10 years"):
        AnalyzeParams(lat=1, lon=1, start=2000, end=2005)
    p = AnalyzeParams(lat=10, lon=20, lat2=12, lon2=24, start=1991, end=2020)
    assert p.center == (11.0, 22.0)


def test_trend_functions_handle_too_little_data():
    assert trends.linear_regression([1, 2], [1, 2])["slope"] is None
    assert trends.linear_regression([3, 3, 3], [1, 2, 3])["slope"] is None  # no spread in x
    assert trends.mann_kendall([1, 2, 3])["trend"] == "insufficient data"
    assert trends.rolling_mean([1, 2, 3, 4, 5, 6])[:4] == [None] * 4


def test_thresholds_need_baseline_data():
    s = pd.Series(20.0, index=pd.date_range("2030-01-01", periods=400))
    with pytest.raises(ValueError, match="No valid data"):
        heatwave.daily_thresholds(s, 1991, 2020)


def test_yearly_metrics_for_year_without_data():
    s = pd.Series(20.0, index=pd.date_range("2000-01-01", "2000-12-31"))
    rows = heatwave.yearly_metrics(s, heatwave.detect_events(s, np.full(366, 25.0)), 1999, 2000)
    assert rows[0]["coverage"] == 0.0 and rows[0]["reliable"] is False and rows[1]["reliable"] is True

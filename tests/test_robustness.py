"""Regression tests for failure modes: bad upstream data, DB outages, error responses, logging."""
import json
import logging
import os
import time

import mongomock
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app import db, logging_config, openmeteo, service
from app.cleaning import clean_series

ORIGIN = {"Origin": "http://localhost:3000"}
Q = "/api/analyze?lat=10&lon=10&start=1991&end=2020"


def _fetch(value):
    def fake(lat, lon, s, e):
        idx = pd.date_range(f"{s}-01-01", f"{e}-12-31")
        return idx.strftime("%Y-%m-%d").tolist(), [value] * len(idx)

    return fake


@pytest.fixture()
def client(monkeypatch):
    from app.main import app

    db.set_db(mongomock.MongoClient()["test"])
    return TestClient(app, raise_server_exceptions=False)


def test_all_null_series_is_a_clean_422_with_cors(client, monkeypatch):
    monkeypatch.setattr(service, "fetch_daily_tmax", _fetch(None))
    r = client.get(Q, headers=ORIGIN)
    assert r.status_code == 422 and "No temperature data" in r.json()["detail"]
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_constant_series_has_no_events_and_valid_json(client, monkeypatch):
    monkeypatch.setattr(service, "fetch_daily_tmax", _fetch(20.0))
    r = client.get(Q)
    assert r.status_code == 200 and r.json()["total_events"] == 0


def test_unhandled_error_is_json_500_with_cors_and_request_id(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(service, "analyze", boom)
    r = client.get(Q, headers=ORIGIN)
    assert r.status_code == 500 and "secret" not in r.text
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert r.headers["x-request-id"] == r.json()["request_id"]


def test_database_outage_degrades_to_uncached_answer(client, monkeypatch):
    class Down:
        def __getitem__(self, _):
            raise ServerSelectionTimeoutError("down")

    db.set_db(Down())
    monkeypatch.setattr(service, "fetch_daily_tmax", _fetch(20.0))
    assert client.get(Q).status_code == 200
    assert client.get("/api/ready").status_code == 503


def test_ready_ok_when_db_up(client):
    assert client.get("/api/ready").json() == {"status": "ok", "database": "up"}


def test_default_rate_limit_applies_to_unmarked_routes(client, monkeypatch):
    monkeypatch.setattr("app.main.geocode", lambda q: [])
    codes = [client.get("/api/geocode?q=paris").status_code for _ in range(65)]
    assert 429 in codes and codes[:60] == [200] * 60


def test_health_is_exempt_from_rate_limit(client):
    assert all(client.get("/api/health").status_code == 200 for _ in range(70))


def test_blank_geocode_query_rejected_without_upstream_call(client, monkeypatch):
    monkeypatch.setattr("app.main.geocode", lambda q: pytest.fail("upstream must not be called"))
    assert client.get("/api/geocode?q=%20%20%20").status_code == 422


def test_validation_errors_are_readable_strings(client):
    for q in ("lat=abc&lon=1", "lat=91&lon=1", "lon=1"):
        detail = client.get(f"/api/analyze?{q}").json()["detail"]
        assert isinstance(detail, str) and ":" in detail


class _Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


def test_client_error_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: calls.append(1) or _Resp(400, {}))
    with pytest.raises(openmeteo.UpstreamError):
        openmeteo._get("http://x", {})
    assert len(calls) == 1


def test_server_error_is_retried_without_trailing_sleep(monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: calls.append(1) or _Resp(503, {}))
    monkeypatch.setattr(openmeteo.time, "sleep", sleeps.append)
    with pytest.raises(openmeteo.UpstreamError):
        openmeteo._get("http://x", {})
    assert len(calls) == 3 and len(sleeps) == 2


def test_non_json_and_wrong_shape_responses(monkeypatch):
    monkeypatch.setattr(openmeteo.time, "sleep", lambda s: None)
    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: _Resp(200, None))
    with pytest.raises(openmeteo.UpstreamError):
        openmeteo._get("http://x", {})
    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: _Resp(200, [1, 2]))
    with pytest.raises(openmeteo.UpstreamError):
        openmeteo._get("http://x", {})


def test_geocode_skips_malformed_results(monkeypatch):
    body = {"results": [{"name": "no coords"}, None, {"name": "ok", "latitude": 1.5, "longitude": 2.5}]}
    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: _Resp(200, body))
    assert [r["name"] for r in openmeteo.geocode("x")] == ["ok"]


def test_cleaning_survives_junk_values():
    dates = pd.date_range("2000-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    s, q = clean_series(dates, [20, "oops", None, float("inf"), 20, 20, 20, 20, 20, 20])
    assert q.total_days == 10
    with pytest.raises(ValueError):
        clean_series([], [])


# ---- logging ---------------------------------------------------------------------------------


def test_json_formatter_fields_and_redaction():
    rec = logging.LogRecord("t", logging.WARNING, __file__, 1, "conn mongodb://user:hunter2@host/db", None, None)
    rec.status = 200
    out = json.loads(logging_config.JsonFormatter().format(rec))
    assert out["level"] == "WARNING" and out["status"] == 200
    assert "hunter2" not in out["message"] and "***" in out["message"]


def test_purge_deletes_only_old_rotated_files(tmp_path):
    live, old, fresh, other = (tmp_path / n for n in ("app.log", "app.log.2020-01-01", "app.log.2099-01-01", "keep.txt"))
    for f in (live, old, fresh, other):
        f.write_text("x")
    long_ago = time.time() - 10 * 86400
    for f in (live, old, other):
        os.utime(f, (long_ago, long_ago))
    assert logging_config.purge_old_logs(tmp_path, 3) == 1
    assert not old.exists() and live.exists() and fresh.exists() and other.exists()
    logging_config.purge_old_logs(tmp_path, 30)  # larger window keeps files that are 10 days old
    assert fresh.exists()


def test_retention_setting_is_validated():
    from pydantic import ValidationError

    from app.config import Settings

    assert Settings(log_retention_days=7).log_retention_days == 7
    with pytest.raises(ValidationError):
        Settings(log_retention_days=0)
    with pytest.raises(ValidationError):
        Settings(log_level="LOUD")


# ---- client-side error reports, log size cap, year bound ---------------------------------------


def test_client_log_accepts_valid_report_and_logs_it(client, caplog):
    with caplog.at_level(logging.WARNING, logger="client"):
        r = client.post("/api/client-log", json={"kind": "error", "message": "boom", "stack": "at x"})
    assert r.status_code == 204
    assert any(rec.name == "client" and rec.kind == "error" for rec in caplog.records)


@pytest.mark.parametrize("body", [{"kind": "x" * 41, "message": "m"}, {"kind": "e", "message": "m" * 501}, {"kind": "e"}, {}])
def test_client_log_rejects_oversized_or_incomplete_reports(client, body):
    assert client.post("/api/client-log", json=body).status_code == 422


def test_client_log_is_rate_limited(client):
    codes = [client.post("/api/client-log", json={"kind": "e", "message": "m"}).status_code for _ in range(12)]
    assert codes[:10] == [204] * 10 and 429 in codes


def test_size_cap_rotates_without_overwriting(tmp_path):
    h = logging_config.RetentionFileHandler(tmp_path, retention_days=3, max_bytes=300)
    h.setFormatter(logging.Formatter("%(message)s"))
    lg = logging.getLogger("sizecap")
    lg.setLevel(logging.WARNING)  # the suite runs with the root level at CRITICAL
    lg.propagate = False
    lg.addHandler(h)
    for i in range(30):
        lg.warning("x" * 100 + str(i))
    h.close()
    lg.removeHandler(h)
    files = sorted(p.name for p in tmp_path.iterdir())
    assert len(files) > 2  # several size-triggered rotations, each kept under a distinct name
    total_lines = sum(len(p.read_text().splitlines()) for p in tmp_path.iterdir())
    assert total_lines == 30  # nothing was overwritten or lost


def test_max_year_is_safe_in_early_january(monkeypatch):
    import datetime as real

    from app import config

    class FakeDate(real.date):
        @classmethod
        def today(cls):
            return cls(2027, 1, 5)

    monkeypatch.setattr(config, "date", FakeDate)
    assert config.settings.max_year == 2025
    FakeDate.today = classmethod(lambda cls: cls(2027, 1, 10))
    assert config.settings.max_year == 2026

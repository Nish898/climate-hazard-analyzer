import mongomock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import db, heatwave, trends
from app.cleaning import clean_series


def _series(years=(1991, 2000), base=25.0):
    idx = pd.date_range(f"{years[0]}-01-01", f"{years[1]}-12-31", freq="D")
    rng = np.random.default_rng(0)
    vals = base + 8 * np.sin((idx.dayofyear - 100) / 365 * 2 * np.pi) + rng.normal(0, 1, len(idx))
    return pd.Series(vals, index=idx)


def test_threshold_shape_and_seasonality():
    thr = heatwave.daily_thresholds(_series(), 1991, 2000)
    assert thr.shape == (366,)
    assert not np.isnan(thr).any()
    assert thr[190] > thr[10]  # summer threshold above winter in this synthetic climate


def test_run_of_three_is_event_two_is_not():
    s = pd.Series(20.0, index=pd.date_range("2000-01-01", "2000-12-31"))
    thr = np.full(366, 25.0)
    s.iloc[10:13] = 30  # 3 days -> event
    s.iloc[50:52] = 30  # 2 days -> not an event
    ev = heatwave.detect_events(s, thr)
    assert len(ev) == 1 and ev.iloc[0].duration == 3 and ev.iloc[0].peak_excess_c == 5.0


def test_gap_breaks_a_run():
    s = pd.Series(20.0, index=pd.date_range("2000-01-01", "2000-12-31"))
    thr = np.full(366, 25.0)
    s.iloc[10:15] = 30
    s.iloc[12] = np.nan
    assert heatwave.detect_events(s, thr).empty  # 2 + 2 days, split by the gap


def test_cleaning_fills_short_gaps_and_flags_bad_values():
    dates = pd.date_range("2000-01-01", periods=30).strftime("%Y-%m-%d").tolist()
    temps = [20.0] * 30
    temps[5] = None          # short gap -> interpolated
    temps[10] = 999.0        # impossible -> removed then interpolated
    temps[15:21] = [None] * 6  # long gap -> stays missing
    s, q = clean_series(dates, temps)
    assert q.out_of_range == 1 and q.still_missing == 6
    assert s.iloc[5] == pytest.approx(20.0) and np.isnan(s.iloc[17])


def test_mann_kendall_detects_trend_and_noise():
    inc = trends.mann_kendall(list(range(20)))
    assert inc["trend"] == "increasing" and inc["p_value"] < 0.01
    flat = trends.mann_kendall([1, 3, 2, 3, 1, 2, 3, 2, 1, 3, 2, 1])
    assert flat["trend"] == "no significant trend"


def test_regression_slope():
    r = trends.linear_regression([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert r["slope"] == pytest.approx(2.0) and r["r2"] == pytest.approx(1.0)


@pytest.fixture()
def client(monkeypatch):
    from app import service
    from app.main import app

    db.set_db(mongomock.MongoClient()["test"])
    calls = {"n": 0}
    full = _series((1990, 2020))

    def fake_fetch(lat, lon, s, e):
        calls["n"] += 1
        sub = full[(full.index.year >= s) & (full.index.year <= e)]
        return sub.index.strftime("%Y-%m-%d").tolist(), sub.round(1).tolist()

    monkeypatch.setattr(service, "fetch_daily_tmax", fake_fetch)
    c = TestClient(app)
    c.calls = calls
    return c


def test_analyze_and_cache(client):
    q = "/api/analyze?lat=28.6&lon=77.2&start=1991&end=2020"
    first = client.get(q).json()
    assert len(first["yearly"]) == 30 and first["meta"]["cached"] is False
    second = client.get(q).json()
    assert second["meta"]["cached"] is True and client.calls["n"] == 1


@pytest.mark.parametrize(
    "q",
    [
        "lat=91&lon=0",
        "lat=0&lon=181",
        "lat=0&lon=0&start=2000&end=2005",
        "lat=0&lon=0&start=1900&end=2000",
        "lat=0&lon=0&lat2=40&lon2=40",
        "lat=0&lon=0&hazard=flood",
    ],
)
def test_bad_input_rejected(client, q):
    assert client.get(f"/api/analyze?{q}").status_code == 422


def test_csv_export(client):
    r = client.get("/api/export.csv?lat=10&lon=10&start=1991&end=2020")
    assert r.status_code == 200 and r.text.startswith("year,events")

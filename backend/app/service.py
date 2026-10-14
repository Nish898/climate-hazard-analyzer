"""Orchestration: cache lookup -> fetch -> clean -> detect -> trend -> store."""
import logging
from datetime import datetime, timezone

import pandas as pd

from . import heatwave, insights, trends
from .cleaning import clean_series
from .config import settings
from .db import get_db
from .openmeteo import fetch_daily_tmax
from .schemas import AnalyzeParams

log = logging.getLogger("service")

ANALYSIS_VERSION = 1  # bump when the hazard logic changes to invalidate cached results


class NoDataError(Exception):
    """The location/period has no usable temperature data."""


def _now():
    return datetime.now(timezone.utc)


def _cache_get(name: str, key: str):
    """Cache read that never fails the request: a broken database just means a cache miss."""
    try:
        return get_db()[name].find_one({"_id": key})
    except Exception as exc:
        log.error("cache read failed (%s): %s", name, exc)
        return None


def _cache_put(name: str, doc: dict) -> None:
    try:
        get_db()[name].replace_one({"_id": doc["_id"]}, doc, upsert=True)
    except Exception as exc:
        log.error("cache write failed (%s): %s", name, exc)


def _load_raw(lat: float, lon: float, need_start: int, need_end: int) -> tuple[list, list, bool]:
    """Returns (dates, temps, from_cache). Refetches the union range on a miss."""
    key = f"{lat:.2f},{lon:.2f}"
    doc = _cache_get("raw_series", key)
    if doc and doc["start_year"] <= need_start and doc["end_year"] >= need_end:
        return doc["dates"], doc["temps"], True
    fs = min(need_start, doc["start_year"]) if doc else need_start
    fe = max(need_end, doc["end_year"]) if doc else need_end
    dates, temps = fetch_daily_tmax(lat, lon, fs, fe)
    _cache_put(
        "raw_series",
        {"_id": key, "start_year": fs, "end_year": fe, "dates": dates, "temps": temps, "fetched_at": _now()},
    )
    return dates, temps, False


TREND_FIELDS = ("events", "heatwave_days", "mean_duration", "max_intensity_c")


def _prepare_series(p: AnalyzeParams, key: str):
    """Cache-aware load + clean. Returns (series, quality, raw_cached, baseline_end)."""
    lat, lon = p.center
    baseline_end = min(settings.baseline_end, settings.max_year)
    raw_start = min(settings.baseline_start, p.start)
    raw_end = min(max(settings.baseline_end, p.end), settings.max_year)
    dates, temps, raw_cached = _load_raw(lat, lon, raw_start, raw_end)
    try:
        series, quality = clean_series(dates, temps)
    except ValueError as exc:
        raise NoDataError(str(exc)) from exc
    if quality.still_missing >= quality.total_days:
        raise NoDataError("No temperature data is available for this location and period.")
    log.info("series cleaned", extra={"key": key, "raw_cached": raw_cached, "quality": quality.to_dict()})
    return series, quality, raw_cached, baseline_end


def _trend_for(rel: list[dict], field: str) -> dict:
    """OLS regression and Mann-Kendall for one yearly metric, over the reliable years only."""
    vals = [r[field] for r in rel]
    return {
        "regression": trends.linear_regression([r["year"] for r in rel], vals),
        "mann_kendall": trends.mann_kendall(vals),
    }


def _build_result(p: AnalyzeParams, series, quality, raw_cached: bool, baseline_end: int) -> dict:
    lat, lon = p.center
    try:
        thr = heatwave.daily_thresholds(series, settings.baseline_start, baseline_end)
    except ValueError as exc:
        raise NoDataError("No valid data in the baseline period for this location.") from exc
    events = heatwave.detect_events(series, thr)
    yearly = heatwave.yearly_metrics(series, events, p.start, p.end)
    rel = [r for r in yearly if r["reliable"]]

    trend = {f: _trend_for(rel, f) for f in TREND_FIELDS}
    for r, ra, rb in zip(
        yearly,
        trends.rolling_mean([r["events"] for r in yearly]),
        trends.rolling_mean([r["heatwave_days"] for r in yearly]),
    ):
        r["events_rolling5"], r["days_rolling5"] = ra, rb

    insight = insights.build_insight(
        yearly, trend["heatwave_days"]["mann_kendall"], trend["heatwave_days"]["regression"], p.start, p.end
    )
    in_range = events[(events.year >= p.start) & (events.year <= p.end)]
    return {
        "location": {"lat": lat, "lon": lon, "box": p.lat2 is not None},
        "range": {"start": p.start, "end": p.end},
        "definition": {
            "hazard": p.hazard,
            "percentile": heatwave.PERCENTILE,
            "min_consecutive_days": heatwave.MIN_DURATION,
            "window_days": heatwave.WINDOW_DAYS,
            "baseline": [settings.baseline_start, baseline_end],
        },
        "yearly": yearly,
        "trends": trend,
        "insight": insight,
        "top_events": in_range.sort_values(["duration", "peak_excess_c"], ascending=False)
        .head(10)
        .to_dict("records"),
        "total_events": int(len(in_range)),
        "quality": quality.to_dict(),
        "meta": {"cached": False, "raw_cached": raw_cached, "generated_at": _now().isoformat()},
    }


def analyze(p: AnalyzeParams) -> dict:
    lat, lon = p.center
    key = f"{p.hazard}|{lat:.2f},{lon:.2f}|{p.start}-{p.end}|v{ANALYSIS_VERSION}"
    hit = _cache_get("analyses", key)
    if hit:
        result = hit["result"]
        result["meta"]["cached"] = True
        log.info("analysis cache hit", extra={"key": key})
        return result

    series, quality, raw_cached, baseline_end = _prepare_series(p, key)
    result = _build_result(p, series, quality, raw_cached, baseline_end)
    _cache_put("analyses", {"_id": key, "result": result, "fetched_at": _now()})
    log.info("analysis computed", extra={"key": key, "total_events": result["total_events"]})
    return result


def to_csv(result: dict) -> str:
    df = pd.DataFrame(result["yearly"])
    return df.to_csv(index=False)

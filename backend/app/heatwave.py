"""Heatwave definition.

A heatwave is >= MIN_DURATION consecutive days whose Tmax exceeds the 95th
percentile of that calendar day, computed over a fixed baseline period using a
+/- WINDOW_DAYS window (so the threshold is smooth and has enough samples).
"""
import warnings

import numpy as np
import pandas as pd

PERCENTILE = 95
WINDOW_DAYS = 7
MIN_DURATION = 3
MIN_YEAR_COVERAGE = 0.8  # years with less valid data are excluded from trend fits


def _day_index(idx: pd.DatetimeIndex) -> np.ndarray:
    """0..365 position in a leap-year calendar (Feb 29 gets its own slot)."""
    doy = idx.dayofyear.to_numpy().copy()
    non_leap_after_feb = (~idx.is_leap_year) & (idx.month > 2)
    doy[non_leap_after_feb] += 1
    return doy - 1


def daily_thresholds(s: pd.Series, base_start: int, base_end: int) -> np.ndarray:
    """95th-percentile Tmax for each of the 366 calendar days."""
    base = s[(s.index.year >= base_start) & (s.index.year <= base_end)].dropna()
    if base.empty:
        raise ValueError("No valid data in baseline period")
    years = base.index.year.to_numpy()
    uniq = np.unique(years)
    mat = np.full((len(uniq), 366), np.nan)
    mat[np.searchsorted(uniq, years), _day_index(base.index)] = base.to_numpy()
    # windows[year, day, k]: the k-th day around `day`, wrapping at the year end
    cols = (np.arange(366)[:, None] + np.arange(-WINDOW_DAYS, WINDOW_DAYS + 1)[None, :]) % 366
    windows = mat[:, cols]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # days with no data at all give NaN
        return np.nanpercentile(windows, PERCENTILE, axis=(0, 2))


def detect_events(s: pd.Series, thr: np.ndarray) -> pd.DataFrame:
    """One row per heatwave: start, end, duration, peak/mean excess over threshold."""
    t = thr[_day_index(s.index)]
    excess = (s.to_numpy() - t)
    hot = np.nan_to_num(excess, nan=-1.0) > 0  # NaN (gap) breaks a run
    padded = np.concatenate([[False], hot, [False]]).astype(np.int8)
    d = np.diff(padded)
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)  # end exclusive
    rows = []
    for a, b in zip(starts, ends):
        if b - a >= MIN_DURATION:
            seg = excess[a:b]
            rows.append(
                {
                    "start": s.index[a].date().isoformat(),
                    "end": s.index[b - 1].date().isoformat(),
                    "year": int(s.index[a].year),
                    "duration": int(b - a),
                    "peak_excess_c": round(float(seg.max()), 2),
                    "mean_excess_c": round(float(seg.mean()), 2),
                    "peak_tmax_c": round(float(s.to_numpy()[a:b].max()), 1),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["start", "end", "year", "duration", "peak_excess_c", "mean_excess_c", "peak_tmax_c"],
    )


def yearly_metrics(s: pd.Series, events: pd.DataFrame, start: int, end: int) -> list[dict]:
    coverage_by_year = s.notna().groupby(s.index.year).mean()
    per_year = {}
    if not events.empty:
        grouped = events.groupby("year")
        per_year = {
            year: (len(g), int(g.duration.sum()), float(g.duration.mean()), int(g.duration.max()), float(g.peak_excess_c.max()))
            for year, g in grouped
        }
    out = []
    for y in range(start, end + 1):
        coverage = float(coverage_by_year.get(y, 0.0))
        n, days, mean_d, max_d, max_i = per_year.get(y, (0, 0, 0.0, 0, 0.0))
        out.append(
            {
                "year": y,
                "events": n,
                "heatwave_days": days,
                "mean_duration": round(mean_d, 2),
                "max_duration": max_d,
                "max_intensity_c": round(max_i, 2),
                "coverage": round(coverage, 3),
                "reliable": coverage >= MIN_YEAR_COVERAGE,
            }
        )
    return out

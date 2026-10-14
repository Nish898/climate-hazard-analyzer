"""Cleaning of noisy daily Tmax series: gaps, spikes, impossible values."""
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

PHYSICAL_MIN_C = -90.0
PHYSICAL_MAX_C = 60.0
SPIKE_C = 15.0          # |x - both neighbours| beyond this is treated as a sensor/reanalysis glitch
MAX_FILL_GAP_DAYS = 3   # longer gaps are left missing rather than invented


@dataclass
class QualityReport:
    total_days: int
    missing_raw: int
    out_of_range: int
    spikes_removed: int
    interpolated: int
    still_missing: int
    pct_valid: float

    def to_dict(self) -> dict:
        return asdict(self)


def clean_series(dates: list[str], temps: list) -> tuple[pd.Series, QualityReport]:
    if len(dates) == 0 or len(dates) != len(temps):
        raise ValueError("Empty or mismatched temperature series")
    # Non-numeric junk becomes NaN (a gap) instead of crashing the request.
    values = pd.to_numeric(pd.Series(temps, dtype="object"), errors="coerce").to_numpy(dtype="float64")
    s = pd.Series(values, index=pd.to_datetime(dates))
    s = s[~s.index.duplicated(keep="first")].sort_index()
    # Reindex to a complete daily calendar so missing days become explicit NaNs.
    s = s.reindex(pd.date_range(s.index[0], s.index[-1], freq="D"))
    s[~np.isfinite(s)] = np.nan
    missing_raw = int(s.isna().sum())

    bad = (s < PHYSICAL_MIN_C) | (s > PHYSICAL_MAX_C)
    out_of_range = int(bad.sum())
    s[bad] = np.nan

    prev, nxt = s.shift(1), s.shift(-1)
    spike = ((s - prev).abs() > SPIKE_C) & ((s - nxt).abs() > SPIKE_C)
    spikes = int(spike.sum())
    s[spike] = np.nan

    before = int(s.isna().sum())
    # Fill only gaps that are short in total; pandas' `limit` would half-fill long gaps.
    isna = s.isna()
    run_id = (isna != isna.shift()).cumsum()
    run_len = isna.groupby(run_id).transform("sum")
    filled = s.interpolate(limit_area="inside")
    s = s.where(~(isna & (run_len <= MAX_FILL_GAP_DAYS)), filled)
    still_missing = int(s.isna().sum())
    total = len(s)
    return s, QualityReport(
        total_days=total,
        missing_raw=missing_raw,
        out_of_range=out_of_range,
        spikes_removed=spikes,
        interpolated=before - still_missing,
        still_missing=still_missing,
        pct_valid=round(100 * (total - still_missing) / total, 2),
    )

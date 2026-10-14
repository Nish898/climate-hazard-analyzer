"""Trend statistics: OLS regression, Mann-Kendall + Sen's slope, rolling mean."""
import math

import numpy as np


def linear_regression(x, y) -> dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) == 0:
        return {"slope": None, "intercept": None, "r2": None, "p_value": None}
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    slope = ((x - xm) * (y - ym)).sum() / sxx
    intercept = ym - slope * xm
    resid = y - (intercept + slope * x)
    sst = ((y - ym) ** 2).sum()
    r2 = 1 - (resid**2).sum() / sst if sst > 0 else 0.0
    # Two-sided p-value for slope via normal approximation of the t statistic.
    se = math.sqrt((resid**2).sum() / (n - 2) / sxx) if n > 2 else float("nan")
    p = math.erfc(abs(slope / se) / math.sqrt(2)) if se and se > 0 else None
    return {"slope": float(slope), "intercept": float(intercept), "r2": float(r2), "p_value": p}


def mann_kendall(y) -> dict:
    """Non-parametric monotonic trend test (tie-corrected) with Sen's slope."""
    y = np.asarray(y, float)
    n = len(y)
    if n < 4:
        return {"trend": "insufficient data", "p_value": None, "tau": None, "sen_slope": None}
    i, j = np.triu_indices(n, k=1)
    diffs = y[j] - y[i]
    s = np.sign(diffs).sum()
    _, counts = np.unique(y, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - (counts * (counts - 1) * (2 * counts + 5)).sum()) / 18
    if var <= 0:
        z = 0.0
    else:
        z = (s - 1) / math.sqrt(var) if s > 0 else (s + 1) / math.sqrt(var) if s < 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    slopes = diffs / (j - i)
    trend = "no significant trend"
    if p < 0.05:
        trend = "increasing" if z > 0 else "decreasing"
    return {
        "trend": trend,
        "p_value": float(p),
        "tau": float(s / (n * (n - 1) / 2)),
        "sen_slope": float(np.median(slopes)),
    }


def rolling_mean(y, window: int = 5) -> list:
    y = np.asarray(y, float)
    out = []
    for i in range(len(y)):
        lo = max(0, i - window + 1)
        out.append(round(float(y[lo : i + 1].mean()), 3) if i >= window - 1 else None)
    return out

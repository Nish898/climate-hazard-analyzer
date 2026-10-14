"""Plain-language insight, deliberately conservative about what the data supports."""
import numpy as np


def build_insight(yearly: list[dict], mk_days: dict, reg_days: dict, start: int, end: int) -> dict:
    rows = [r for r in yearly if r["reliable"]]
    caveats = []
    excluded = len(yearly) - len(rows)
    if excluded:
        caveats.append(f"{excluded} year(s) with <80% valid data were excluded from trend statistics.")
    if len(rows) < 10:
        return {
            "headline": f"Only {len(rows)} usable years: too few to say anything reliable about a trend.",
            "significant": False,
            "pct_change": None,
            "caveats": caveats,
        }

    days = np.array([r["heatwave_days"] for r in rows], float)
    half = max(len(rows) // 2, 1)
    first, last = days[:half].mean(), days[-half:].mean()
    first_y, last_y = rows[0]["year"], rows[-1]["year"]
    significant = mk_days.get("p_value") is not None and mk_days["p_value"] < 0.05
    pct = None
    if first >= 1.0:
        pct = round(100 * (last - first) / first, 1)
    else:
        caveats.append("Early-period average is below 1 heatwave day/year, so a percent change would be misleading.")

    period = f"{first_y}-{last_y}"
    if significant and pct is not None:
        direction = "increased" if pct > 0 else "decreased"
        headline = (
            f"Heatwave days have {direction} by about {abs(pct):.0f}% between the first and second half of "
            f"{period} ({first:.1f} to {last:.1f} days/year). The trend is statistically significant "
            f"(Mann-Kendall p={mk_days['p_value']:.3f})."
        )
    elif significant:
        headline = (
            f"Heatwave days show a statistically significant {mk_days['trend']} trend over {period} "
            f"(Sen's slope {mk_days['sen_slope']:+.2f} days/yr, p={mk_days['p_value']:.3f})."
        )
    else:
        headline = (
            f"No statistically significant trend in heatwave days over {period} "
            f"(p={mk_days['p_value']:.2f}); year-to-year variability dominates."
            if mk_days.get("p_value") is not None
            else f"No trend could be estimated over {period}."
        )
    caveats.append("Results come from ERA5 reanalysis at a single grid point, not weather-station records.")
    caveats.append("Heatwave counts are noisy year to year; short ranges can mislead.")
    return {"headline": headline, "significant": significant, "pct_change": pct, "caveats": caveats}

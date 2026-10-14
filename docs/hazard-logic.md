# Hazard logic

## Data

Daily maximum 2 m temperature (`temperature_2m_max`, degC) from the Open-Meteo historical archive (ERA5
reanalysis, ~25 km grid), requested in degrees Celsius so no unit conversion is needed. The fetch always includes the baseline period (1991-2020) plus the selected range.

## Cleaning (`cleaning.py`)

| Issue | Handling |
|---|---|
| Non-numeric or non-finite values | Treated as gaps (never crash the request) |
| Missing/duplicate/unordered days | Reindexed to a complete daily calendar; gaps become explicit NaN |
| Physically impossible values (outside -90..60 degC) | Removed |
| Isolated spikes (differ >15 degC from both neighbours) | Removed |
| Short gaps (<=3 days in total) | Linear interpolation |
| Longer gaps | Left missing, never invented; they break heatwave runs |
| Years with <80% valid days | Marked `reliable=false`, drawn grey, excluded from trend statistics |

A quality report (percent valid, counts per category) is returned with every analysis.

## Heatwave definition (`heatwave.py`)

1. **Threshold**: for each calendar day (366 slots, so Feb 29 has its own), the 95th percentile of Tmax
   over the baseline years 1991-2020, using a +/-7-day window around that day (15 days x 30 years = 450
   samples). The window keeps the threshold smooth and statistically stable.
2. **Event**: 3 or more consecutive days with Tmax strictly above that day's threshold.
3. **Metrics per event**: start, end, duration, peak and mean excess over the threshold, peak Tmax.
4. **Metrics per year** (events are assigned to the year in which they start): event count, heatwave days,
   mean and max duration, max intensity.

The baseline is fixed regardless of the selected range, so different ranges are comparable.

## Trend statistics (`trends.py`)

- **OLS regression** (slope, R-squared, p-value) on yearly values.
- **Mann-Kendall** with tie correction: a non-parametric monotonic trend test, robust to outliers and to
  non-normal count data. **Sen's slope** is the matching robust estimate of change per year.
- **5-year rolling mean** for visual smoothing.
- Fitted to heatwave days, event count, mean duration and peak intensity.

## How insights are worded (`insights.py`)

- A percent change is reported only if the Mann-Kendall p < 0.05 **and** the early-period mean is at least
  1 heatwave day/year (otherwise the percentage is unstable).
- The percent compares the mean of the first half of usable years with the second half.
- If the trend is not significant, the app says so rather than describing noise as a trend.
- Fewer than 10 usable years produces no trend claim at all.
- Caveats are always shown (reanalysis, not stations; interannual variability).

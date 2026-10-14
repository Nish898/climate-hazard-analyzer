"""Safe client for the Open-Meteo archive + geocoding APIs.

Only fixed hosts from settings are contacted; user input is passed as validated
query parameters, never concatenated into URLs.
"""
import logging
import time

import httpx

from .config import settings

log = logging.getLogger("openmeteo")


class UpstreamError(Exception):
    pass


def _get(url: str, params: dict) -> dict:
    last: Exception | None = None
    attempts = max(settings.http_retries, 1)
    for attempt in range(attempts):
        started = time.perf_counter()
        try:
            r = httpx.get(url, params=params, timeout=settings.http_timeout_s)
            log.info(
                "upstream response",
                extra={"url": url, "status": r.status_code, "attempt": attempt + 1,
                       "duration_ms": round((time.perf_counter() - started) * 1000, 1)},
            )
            if r.status_code != 429 and r.status_code < 500 and r.status_code != 200:
                # a 4xx will not fix itself, so do not retry
                raise UpstreamError(f"upstream rejected request ({r.status_code})")
            if r.status_code != 200:
                last = UpstreamError(f"upstream status {r.status_code}")
            else:
                body = r.json()
                if not isinstance(body, dict):
                    raise UpstreamError("Unexpected response shape from Open-Meteo")
                return body
        except UpstreamError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
        log.warning("upstream attempt failed", extra={"url": url, "attempt": attempt + 1, "error": str(last)})
        if attempt < attempts - 1:
            time.sleep(0.5 * 2**attempt)
    log.error("upstream unavailable after retries", extra={"url": url, "attempts": attempts})
    raise UpstreamError(f"Open-Meteo unavailable: {last}")


def fetch_daily_tmax(lat: float, lon: float, start_year: int, end_year: int) -> tuple[list[str], list]:
    """Returns (ISO dates, tmax in degC with None for gaps)."""
    data = _get(
        settings.open_meteo_archive_url,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "temperature_2m_max",
            "temperature_unit": "celsius",
            "timezone": "auto",
        },
    )
    daily = data.get("daily") or {}
    dates, temps = daily.get("time"), daily.get("temperature_2m_max")
    if not dates or temps is None or len(dates) != len(temps):
        raise UpstreamError("Unexpected response shape from Open-Meteo")
    return dates, temps


def geocode(query: str, count: int = 5) -> list[dict]:
    data = _get(
        settings.open_meteo_geocode_url,
        {"name": query, "count": count, "language": "en", "format": "json"},
    )
    return [
        {
            "name": r.get("name"),
            "admin1": r.get("admin1"),
            "country": r.get("country"),
            "lat": r["latitude"],
            "lon": r["longitude"],
        }
        for r in data.get("results") or []
        if isinstance(r, dict) and isinstance(r.get("latitude"), (int, float)) and isinstance(r.get("longitude"), (int, float))
    ]

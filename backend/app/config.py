from datetime import date

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "climate_hazards"
    allow_mongomock_fallback: bool = True

    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_default: str = "60/minute"
    rate_limit_analyze: str = "15/minute"

    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"
    open_meteo_geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    http_timeout_s: float = 30.0
    http_retries: int = Field(default=3, ge=1, le=10)

    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "logs"
    # Days to keep rotated log files.
    log_retention_days: int = Field(default=3, ge=1)
    # Rotate the live file early past this size (MB).
    log_max_mb: int = Field(default=50, ge=1)
    rate_limit_client_log: str = "10/minute"

    cache_ttl_days: int = 30
    # Baseline used for percentile thresholds (WMO standard 30-year normal).
    baseline_start: int = 1991
    baseline_end: int = 2020
    min_year: int = 1950
    max_box_degrees: float = 5.0

    @field_validator("log_level")
    @classmethod
    def _valid_level(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
        return v

    @property
    def max_year(self) -> int:
        """Last year the archive fully covers. It lags a few days, so before 10 Jan that is two years back."""
        today = date.today()
        return today.year - 1 if (today.month, today.day) >= (1, 10) else today.year - 2

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

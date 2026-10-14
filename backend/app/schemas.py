"""Validated request parameters. Every user-controlled value is bounds-checked here."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .config import settings

HAZARDS = ("heatwave",)


class AnalyzeParams(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    # Optional opposite corner of a lat/lon box; analysis uses the box centre.
    lat2: Optional[float] = Field(default=None, ge=-90, le=90)
    lon2: Optional[float] = Field(default=None, ge=-180, le=180)
    start: int = Field(default=1990)
    end: int = Field(default=2020)
    hazard: Literal["heatwave"] = "heatwave"

    @model_validator(mode="after")
    def _check(self):
        if (self.lat2 is None) != (self.lon2 is None):
            raise ValueError("Provide both lat2 and lon2 for a box, or neither")
        if self.lat2 is not None:
            if abs(self.lat2 - self.lat) > settings.max_box_degrees or abs(self.lon2 - self.lon) > settings.max_box_degrees:
                raise ValueError(f"Box may not exceed {settings.max_box_degrees} degrees per side")
        if not (settings.min_year <= self.start <= self.end <= settings.max_year):
            raise ValueError(f"Years must satisfy {settings.min_year} <= start <= end <= {settings.max_year}")
        if self.end - self.start < 9:
            raise ValueError("Range must span at least 10 years for a meaningful trend")
        return self

    @property
    def center(self) -> tuple[float, float]:
        if self.lat2 is None:
            return round(self.lat, 2), round(self.lon, 2)
        return round((self.lat + self.lat2) / 2, 2), round((self.lon + self.lon2) / 2, 2)

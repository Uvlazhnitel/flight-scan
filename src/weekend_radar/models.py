"""Core internal pydantic models for Weekend Radar."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Destination(BaseModel):
    """A destination that can be considered for weekend flight deals."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=3, max_length=3)
    city: str = Field(min_length=1)
    country: str = Field(min_length=1)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    tags: list[str] = Field(default_factory=list)
    nature_score: int = Field(default=0, ge=0, le=10)
    enabled: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        """Normalize airport codes to uppercase."""

        return value.upper()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        """Normalize destination tags for predictable matching."""

        return [value.strip().lower() for value in values]


class WeekendWindow(BaseModel):
    """Rules that define which outbound and return timing counts as a weekend trip."""

    departure_weekdays: list[int] = Field(default_factory=lambda: [4, 5])
    return_weekdays: list[int] = Field(default_factory=lambda: [6, 0])
    min_nights: int = Field(default=2, ge=1)
    max_nights: int = Field(default=3, ge=1)

    @field_validator("departure_weekdays", "return_weekdays")
    @classmethod
    def validate_weekdays(cls, values: list[int]) -> list[int]:
        """Ensure weekday values are unique and within Python's 0-6 weekday range."""

        if not values:
            raise ValueError("weekday lists must not be empty")
        if any(value < 0 or value > 6 for value in values):
            raise ValueError("weekday values must be between 0 and 6")
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_night_range(self) -> Self:
        """Ensure the configured weekend night range is coherent."""

        if self.max_nights < self.min_nights:
            raise ValueError("max_nights must be greater than or equal to min_nights")
        return self


class FlightOffer(BaseModel):
    """A round-trip flight offer returned by a provider and evaluated by the pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True)

    provider: str = Field(min_length=1)
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    depart_at: datetime
    arrive_at: datetime
    return_depart_at: datetime
    return_arrive_at: datetime
    price_eur: int = Field(ge=0)
    currency: str = Field(default="EUR", min_length=1)
    airline: str | None = None
    stops: int = Field(default=0, ge=0)
    booking_url: str | None = None
    checked_at: datetime

    @field_validator("origin", "destination")
    @classmethod
    def normalize_airport_code(cls, value: str) -> str:
        """Normalize airport codes to uppercase."""

        return value.upper()

    @field_validator("checked_at")
    @classmethod
    def ensure_checked_at_timezone_aware(cls, value: datetime) -> datetime:
        """Require timezone-aware timestamps for provider snapshot times."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_trip_timeline(self) -> Self:
        """Ensure outbound and return timestamps form a valid chronological trip."""

        if self.arrive_at < self.depart_at:
            raise ValueError("arrive_at must not be earlier than depart_at")
        if self.return_depart_at < self.arrive_at:
            raise ValueError("return_depart_at must not be earlier than arrive_at")
        if self.return_arrive_at < self.return_depart_at:
            raise ValueError("return_arrive_at must not be earlier than return_depart_at")
        return self


class DealScore(BaseModel):
    """A transparent score describing why a flight offer is attractive."""

    threshold_eur: int = Field(gt=0)
    price_margin_eur: int = Field(ge=0)
    destination_bonus: int = Field(ge=0)
    total_score: int = Field(ge=0)


class DealCandidate(BaseModel):
    """A qualifying offer enriched with destination context and computed score data."""

    offer: FlightOffer
    destination: Destination
    score: DealScore


class AppConfig(BaseModel):
    """Validated non-secret runtime config loaded from YAML."""

    model_config = ConfigDict(str_strip_whitespace=True)

    destinations: list[Destination] = Field(default_factory=list)
    weekend_window: WeekendWindow
    default_price_threshold_eur: int = Field(gt=0)
    destination_thresholds_eur: dict[str, int] = Field(default_factory=dict)

    @field_validator("destination_thresholds_eur")
    @classmethod
    def normalize_threshold_map(cls, values: dict[str, int]) -> dict[str, int]:
        """Normalize destination-code keys and validate positive thresholds."""

        normalized: dict[str, int] = {}
        for code, threshold in values.items():
            if threshold <= 0:
                raise ValueError("destination thresholds must be positive")
            normalized[code.upper()] = threshold
        return normalized

    @model_validator(mode="after")
    def validate_threshold_targets(self) -> Self:
        """Ensure destination-specific thresholds point to known destination codes."""

        known_codes = {destination.code for destination in self.destinations}
        unknown_codes = set(self.destination_thresholds_eur) - known_codes
        if unknown_codes:
            unknown_list = ", ".join(sorted(unknown_codes))
            raise ValueError(f"threshold overrides reference unknown destinations: {unknown_list}")
        return self


class PipelineResult(BaseModel):
    """A small result object for the bootstrap runner."""

    status: str
    destination_count: int = 0
    source: str
    message: str

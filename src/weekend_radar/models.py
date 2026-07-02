"""Shared lightweight models for the project skeleton."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class Destination(BaseModel):
    """A configurable destination route from Riga."""

    origin: str = Field(default="RIX")
    destination: str
    city: str
    country: str
    enabled: bool = True
    threshold_eur: int = Field(gt=0)


class FlightOption(BaseModel):
    """A placeholder flight option returned by a provider."""

    origin: str
    destination: str
    depart_date: date
    return_date: date
    total_price_eur: int = Field(ge=0)
    currency: str = "EUR"
    provider: str = "mock"


class PipelineResult(BaseModel):
    """A small result object for the milestone-one runner."""

    status: str
    destination_count: int = 0
    source: str
    message: str

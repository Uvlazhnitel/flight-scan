"""Stable provider boundary for future flight sources."""

from __future__ import annotations

from typing import Protocol

from weekend_radar.models import Destination, FlightOffer, WeekendWindow


class ProviderError(RuntimeError):
    """Base error raised by real or mock flight providers."""


class ProviderConfigurationError(ProviderError):
    """Raised when a configured provider is missing required local setup."""


class FlightProvider(Protocol):
    """Minimal contract for flight providers."""

    async def search_weekend_flights(
        self,
        origin: str,
        destination: Destination,
        weekend_window: WeekendWindow,
    ) -> list[FlightOffer]:
        """Return candidate weekend flights for one destination and one weekend window."""

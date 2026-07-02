"""Stable provider boundary for future flight sources."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from weekend_radar.models import Destination, FlightOffer


class FlightProvider(Protocol):
    """Minimal contract for flight providers."""

    async def search_weekend_flights(
        self,
        origin: str,
        destinations: Sequence[Destination],
    ) -> list[FlightOffer]:
        """Return candidate weekend flights for the given origin and destinations."""

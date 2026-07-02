"""Mock provider that returns deterministic local placeholder flights."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from weekend_radar.models import Destination, FlightOption


class MockFlightProvider:
    """A deterministic provider used for bootstrap and tests."""

    async def search_weekend_flights(
        self,
        origin: str,
        destinations: Sequence[Destination],
    ) -> list[FlightOption]:
        flights: list[FlightOption] = []
        base_departure = date(2026, 7, 3)

        for index, destination in enumerate(destinations):
            flights.append(
                FlightOption(
                    origin=origin,
                    destination=destination.destination,
                    depart_date=base_departure + timedelta(days=index),
                    return_date=base_departure + timedelta(days=index + 2),
                    total_price_eur=max(25, destination.threshold_eur - 10),
                    provider="mock",
                )
            )

        return flights

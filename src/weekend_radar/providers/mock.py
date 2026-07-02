"""Mock provider that returns deterministic local placeholder flights."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from weekend_radar.models import Destination, FlightOffer


class MockFlightProvider:
    """A deterministic provider used for bootstrap and tests."""

    async def search_weekend_flights(
        self,
        origin: str,
        destinations: Sequence[Destination],
    ) -> list[FlightOffer]:
        flights: list[FlightOffer] = []
        base_departure = datetime(2026, 7, 3, 18, 0, tzinfo=UTC)
        checked_at = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

        for index, destination in enumerate(destinations):
            depart_at = base_departure + timedelta(days=index)
            arrive_at = depart_at + timedelta(hours=3)
            return_depart_at = depart_at + timedelta(days=2, hours=2)
            return_arrive_at = return_depart_at + timedelta(hours=3)
            flights.append(
                FlightOffer(
                    provider="mock",
                    origin=origin,
                    destination=destination.code,
                    depart_at=depart_at,
                    arrive_at=arrive_at,
                    return_depart_at=return_depart_at,
                    return_arrive_at=return_arrive_at,
                    price_eur=max(25, 60 + index * 20),
                    currency="EUR",
                    airline="Mock Air",
                    stops=index % 2,
                    booking_url=f"https://example.com/book/{destination.code.lower()}",
                    checked_at=checked_at,
                )
            )

        return flights

"""Deterministic mock provider that returns realistic fake flight offers."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from urllib.parse import quote_plus

from weekend_radar.models import Destination, FlightOffer, WeekendWindow


class MockFlightProvider:
    """A deterministic provider that generates realistic fake offers without network calls."""

    provider_name = "mock"

    async def search_weekend_flights(
        self,
        origin: str,
        destination: Destination,
        weekend_window: WeekendWindow,
    ) -> list[FlightOffer]:
        """Return a deterministic mix of fake offers for a destination and weekend window."""

        base_checked_at = self._build_checked_at(weekend_window)
        destination_seed = sum(ord(character) for character in destination.code)
        price_offset = destination_seed % 9

        return [
            self._build_offer(
                offer_key="excellent_direct",
                origin=origin,
                destination=destination,
                weekend_window=weekend_window,
                outbound_departure=self._combine(weekend_window.depart_date, time(17, 35)),
                outbound_arrival=self._combine(weekend_window.depart_date, time(20, 10)),
                return_departure=self._combine(weekend_window.return_date, time(18, 25)),
                return_arrival=self._combine(weekend_window.return_date, time(21, 0)),
                price_eur=49 + price_offset,
                airline="Air Baltic Mock",
                stops=0,
                checked_at=base_checked_at,
            ),
            self._build_offer(
                offer_key="cheap_bad_timing",
                origin=origin,
                destination=destination,
                weekend_window=weekend_window,
                outbound_departure=self._combine(weekend_window.depart_date, time(5, 10)),
                outbound_arrival=self._combine(weekend_window.depart_date, time(7, 45)),
                return_departure=self._combine(weekend_window.return_date, time(23, 40)),
                return_arrival=self._combine(weekend_window.return_date, time(23, 59)),
                price_eur=44 + price_offset,
                airline="Budget Mock",
                stops=0,
                checked_at=base_checked_at,
            ),
            self._build_offer(
                offer_key="expensive_good_timing",
                origin=origin,
                destination=destination,
                weekend_window=weekend_window,
                outbound_departure=self._combine(weekend_window.depart_date, time(18, 5)),
                outbound_arrival=self._combine(weekend_window.depart_date, time(20, 35)),
                return_departure=self._combine(weekend_window.return_date, time(17, 55)),
                return_arrival=self._combine(weekend_window.return_date, time(20, 25)),
                price_eur=189 + price_offset,
                airline="Premium Mock",
                stops=0,
                checked_at=base_checked_at,
            ),
            self._build_offer(
                offer_key="one_stop",
                origin=origin,
                destination=destination,
                weekend_window=weekend_window,
                outbound_departure=self._combine(weekend_window.depart_date, time(16, 20)),
                outbound_arrival=self._combine(weekend_window.depart_date, time(21, 50)),
                return_departure=self._combine(weekend_window.return_date, time(16, 45)),
                return_arrival=self._combine(weekend_window.return_date, time(22, 5)),
                price_eur=79 + price_offset,
                airline="Connector Mock",
                stops=1,
                checked_at=base_checked_at,
            ),
            self._build_offer(
                offer_key="duplicate_like_a",
                origin=origin,
                destination=destination,
                weekend_window=weekend_window,
                outbound_departure=self._combine(weekend_window.depart_date, time(17, 40)),
                outbound_arrival=self._combine(weekend_window.depart_date, time(20, 15)),
                return_departure=self._combine(weekend_window.return_date, time(18, 20)),
                return_arrival=self._combine(weekend_window.return_date, time(20, 55)),
                price_eur=57 + price_offset,
                airline="Air Baltic Mock",
                stops=0,
                checked_at=base_checked_at,
            ),
            self._build_offer(
                offer_key="duplicate_like_b",
                origin=origin,
                destination=destination,
                weekend_window=weekend_window,
                outbound_departure=self._combine(weekend_window.depart_date, time(17, 40)),
                outbound_arrival=self._combine(weekend_window.depart_date, time(20, 15)),
                return_departure=self._combine(weekend_window.return_date, time(18, 20)),
                return_arrival=self._combine(weekend_window.return_date, time(20, 55)),
                price_eur=57 + price_offset,
                airline="Air Baltic Mock Partner",
                stops=0,
                checked_at=base_checked_at.replace(minute=7),
            ),
        ]

    def _build_offer(
        self,
        *,
        offer_key: str,
        origin: str,
        destination: Destination,
        weekend_window: WeekendWindow,
        outbound_departure: datetime,
        outbound_arrival: datetime,
        return_departure: datetime,
        return_arrival: datetime,
        price_eur: int,
        airline: str,
        stops: int,
        checked_at: datetime,
    ) -> FlightOffer:
        """Construct one deterministic flight offer."""

        return FlightOffer(
            provider=self.provider_name,
            origin=origin,
            destination=destination.code,
            depart_at=outbound_departure,
            arrive_at=outbound_arrival,
            return_depart_at=return_departure,
            return_arrive_at=return_arrival,
            price_eur=price_eur,
            currency="EUR",
            airline=airline,
            stops=stops,
            booking_url=self._booking_url(destination.code, weekend_window, offer_key),
            checked_at=checked_at,
        )

    def _build_checked_at(self, weekend_window: WeekendWindow) -> datetime:
        """Create a stable checked-at timestamp from the requested depart date."""

        return datetime.combine(weekend_window.depart_date, time(9, 0), tzinfo=UTC)

    def _combine(self, day: date, moment: time) -> datetime:
        """Build a UTC-aware datetime from a date and time."""

        return datetime.combine(day, moment, tzinfo=UTC)

    def _booking_url(
        self,
        destination_code: str,
        weekend_window: WeekendWindow,
        offer_key: str,
    ) -> str:
        """Create a deterministic fake booking URL."""

        encoded_pattern = quote_plus(weekend_window.pattern_name)
        return (
            f"https://mock.weekend-radar.test/book/{destination_code.lower()}"
            f"?pattern={encoded_pattern}&offer={offer_key}"
        )

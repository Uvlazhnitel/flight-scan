from datetime import UTC, datetime

from weekend_radar.filters import enabled_destinations, weekend_flights
from weekend_radar.models import Destination, FlightOffer, WeekendSearchRules


def test_enabled_destinations_keeps_only_enabled_rows() -> None:
    destinations = [
        Destination(
            code="FCO",
            city="Rome",
            country="Italy",
            nature_score=3,
        ),
        Destination(
            code="BCN",
            city="Barcelona",
            country="Spain",
            nature_score=4,
            enabled=False,
        ),
    ]

    result = enabled_destinations(destinations)

    assert [item.code for item in result] == ["FCO"]


def test_weekend_flights_keeps_only_weekend_shape() -> None:
    weekend_rules = WeekendSearchRules()
    flights = [
        FlightOffer(
            provider="mock",
            origin="RIX",
            destination="FCO",
            depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
            return_depart_at=datetime(2026, 7, 5, 20, 0, tzinfo=UTC),
            return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
            price_eur=99,
            checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        ),
        FlightOffer(
            provider="mock",
            origin="RIX",
            destination="BCN",
            depart_at=datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 1, 21, 0, tzinfo=UTC),
            return_depart_at=datetime(2026, 7, 2, 20, 0, tzinfo=UTC),
            return_arrive_at=datetime(2026, 7, 2, 23, 0, tzinfo=UTC),
            price_eur=89,
            checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        ),
    ]

    result = weekend_flights(flights, weekend_rules)

    assert [item.destination for item in result] == ["FCO"]

from datetime import date

from weekend_radar.filters import enabled_destinations, weekend_flights
from weekend_radar.models import Destination, FlightOption


def test_enabled_destinations_keeps_only_enabled_rows() -> None:
    destinations = [
        Destination(destination="FCO", city="Rome", country="Italy", threshold_eur=120),
        Destination(
            destination="BCN",
            city="Barcelona",
            country="Spain",
            threshold_eur=150,
            enabled=False,
        ),
    ]

    result = enabled_destinations(destinations)

    assert [item.destination for item in result] == ["FCO"]


def test_weekend_flights_keeps_only_weekend_shape() -> None:
    flights = [
        FlightOption(
            origin="RIX",
            destination="FCO",
            depart_date=date(2026, 7, 3),
            return_date=date(2026, 7, 5),
            total_price_eur=99,
        ),
        FlightOption(
            origin="RIX",
            destination="BCN",
            depart_date=date(2026, 7, 1),
            return_date=date(2026, 7, 2),
            total_price_eur=89,
        ),
    ]

    result = weekend_flights(flights)

    assert [item.destination for item in result] == ["FCO"]

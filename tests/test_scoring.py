from datetime import date

from weekend_radar.models import Destination, FlightOption
from weekend_radar.scoring import qualifies_price, score_flight


def test_qualifies_price_checks_threshold() -> None:
    destination = Destination(
        destination="FCO",
        city="Rome",
        country="Italy",
        threshold_eur=120,
    )
    cheap_flight = FlightOption(
        origin="RIX",
        destination="FCO",
        depart_date=date(2026, 7, 3),
        return_date=date(2026, 7, 5),
        total_price_eur=90,
    )
    expensive_flight = cheap_flight.model_copy(update={"total_price_eur": 140})

    assert qualifies_price(cheap_flight, destination)
    assert not qualifies_price(expensive_flight, destination)


def test_score_flight_rewards_margin_below_threshold() -> None:
    destination = Destination(
        destination="ATH",
        city="Athens",
        country="Greece",
        threshold_eur=170,
    )
    flight = FlightOption(
        origin="RIX",
        destination="ATH",
        depart_date=date(2026, 7, 3),
        return_date=date(2026, 7, 5),
        total_price_eur=130,
    )

    assert score_flight(flight, destination) == 40

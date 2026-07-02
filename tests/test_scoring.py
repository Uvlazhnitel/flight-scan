from datetime import UTC, datetime

from weekend_radar.models import AppConfig, Destination, FlightOffer, WeekendWindow
from weekend_radar.scoring import build_deal_candidate, qualifies_price, score_flight


def test_qualifies_price_checks_threshold() -> None:
    destination = Destination(
        code="FCO",
        city="Rome",
        country="Italy",
        nature_score=3,
    )
    app_config = AppConfig(
        destinations=[destination],
        weekend_window=WeekendWindow(),
        default_price_threshold_eur=140,
        destination_thresholds_eur={"FCO": 120},
    )
    cheap_flight = FlightOffer(
        provider="mock",
        origin="RIX",
        destination="FCO",
        depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
        arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
        return_depart_at=datetime(2026, 7, 5, 20, 0, tzinfo=UTC),
        return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
        price_eur=90,
        checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )
    expensive_flight = cheap_flight.model_copy(update={"price_eur": 140})

    assert qualifies_price(cheap_flight, destination, app_config)
    assert not qualifies_price(expensive_flight, destination, app_config)


def test_score_flight_returns_structured_score() -> None:
    destination = Destination(
        code="ATH",
        city="Athens",
        country="Greece",
        nature_score=5,
    )
    app_config = AppConfig(
        destinations=[destination],
        weekend_window=WeekendWindow(),
        default_price_threshold_eur=200,
        destination_thresholds_eur={},
    )
    flight = FlightOffer(
        provider="mock",
        origin="RIX",
        destination="ATH",
        depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
        arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
        return_depart_at=datetime(2026, 7, 5, 20, 0, tzinfo=UTC),
        return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
        price_eur=130,
        checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    score = score_flight(flight, destination, app_config)

    assert score.threshold_eur == 200
    assert score.price_margin_eur == 70
    assert score.destination_bonus == 5
    assert score.total_score == 75


def test_build_deal_candidate_returns_none_for_expensive_offer() -> None:
    destination = Destination(
        code="BCN",
        city="Barcelona",
        country="Spain",
        nature_score=4,
    )
    app_config = AppConfig(
        destinations=[destination],
        weekend_window=WeekendWindow(),
        default_price_threshold_eur=100,
        destination_thresholds_eur={},
    )
    flight = FlightOffer(
        provider="mock",
        origin="RIX",
        destination="BCN",
        depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
        arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
        return_depart_at=datetime(2026, 7, 5, 20, 0, tzinfo=UTC),
        return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
        price_eur=130,
        checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    assert build_deal_candidate(flight, destination, app_config) is None

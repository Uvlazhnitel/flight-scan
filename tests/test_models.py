from datetime import UTC, date, datetime, time

import pytest
from pydantic import ValidationError

from weekend_radar.models import (
    AppConfig,
    Destination,
    FlightOffer,
    OfferFilterRules,
    WeekendSearchRules,
    WeekendWindow,
)


def test_destination_normalizes_code_and_tags() -> None:
    destination = Destination(
        code="fco",
        city="Rome",
        country="Italy",
        tags=[" Food ", "City"],
        nature_score=3,
    )

    assert destination.code == "FCO"
    assert destination.tags == ["food", "city"]
    assert destination.enabled is True


def test_destination_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValidationError):
        Destination(
            code="ATH",
            city="Athens",
            country="Greece",
            lat=120,
            nature_score=5,
        )


def test_flight_offer_requires_timezone_aware_checked_at() -> None:
    with pytest.raises(ValidationError):
        FlightOffer(
            provider="mock",
            origin="RIX",
            destination="ATH",
            depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
            return_depart_at=datetime(2026, 7, 5, 20, 0, tzinfo=UTC),
            return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
            price_eur=80,
            checked_at=datetime(2026, 7, 1, 9, 0),
        )


def test_flight_offer_rejects_invalid_timeline() -> None:
    with pytest.raises(ValidationError):
        FlightOffer(
            provider="mock",
            origin="RIX",
            destination="ATH",
            depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
            return_depart_at=datetime(2026, 7, 3, 20, 0, tzinfo=UTC),
            return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
            price_eur=80,
            checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        )


def test_weekend_window_requires_matching_nights() -> None:
    with pytest.raises(ValidationError):
        WeekendWindow(
            depart_date=date(2026, 7, 3),
            return_date=date(2026, 7, 5),
            pattern_name="friday_evening_to_sunday_evening",
            preferred_outbound_start_time=time(hour=15),
            preferred_outbound_end_time=time(hour=22, minute=30),
            preferred_return_start_time=time(hour=15),
            preferred_return_end_time=time(hour=23),
            nights=3,
        )


def test_flight_offer_rejects_negative_stops() -> None:
    with pytest.raises(ValidationError):
        FlightOffer(
            provider="mock",
            origin="RIX",
            destination="ATH",
            depart_at=datetime(2026, 7, 3, 18, 0, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 3, 21, 0, tzinfo=UTC),
            return_depart_at=datetime(2026, 7, 5, 20, 0, tzinfo=UTC),
            return_arrive_at=datetime(2026, 7, 5, 23, 0, tzinfo=UTC),
            price_eur=80,
            stops=-1,
            checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        )


def test_app_config_normalizes_threshold_overrides() -> None:
    app_config = AppConfig(
        destinations=[
            Destination(
                code="bcn",
                city="Barcelona",
                country="Spain",
                nature_score=4,
            )
        ],
        weekend_search=WeekendSearchRules(),
        offer_filters=OfferFilterRules(),
        default_price_threshold_eur=140,
        destination_thresholds_eur={"bcn": 150},
    )

    assert app_config.destination_thresholds_eur == {"BCN": 150}


def test_app_config_rejects_unknown_threshold_override_code() -> None:
    with pytest.raises(ValidationError):
        AppConfig(
            destinations=[
                Destination(
                    code="BCN",
                    city="Barcelona",
                    country="Spain",
                    nature_score=4,
                )
            ],
            weekend_search=WeekendSearchRules(),
            offer_filters=OfferFilterRules(),
            default_price_threshold_eur=140,
            destination_thresholds_eur={"ATH": 150},
        )


def test_offer_filter_rules_have_expected_defaults() -> None:
    rules = OfferFilterRules()

    assert rules.max_price_eur == 120
    assert rules.direct_only is True

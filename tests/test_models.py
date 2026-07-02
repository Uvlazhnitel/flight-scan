from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from weekend_radar.models import AppConfig, Destination, FlightOffer, WeekendWindow


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


def test_weekend_window_requires_valid_night_range() -> None:
    with pytest.raises(ValidationError):
        WeekendWindow(
            departure_weekdays=[4, 5],
            return_weekdays=[6, 0],
            min_nights=3,
            max_nights=2,
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
        weekend_window=WeekendWindow(),
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
            weekend_window=WeekendWindow(),
            default_price_threshold_eur=140,
            destination_thresholds_eur={"ATH": 150},
        )

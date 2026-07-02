from datetime import date

from weekend_radar.dates import is_weekend_date, is_weekend_trip, next_weekend_start


def test_is_weekend_date_distinguishes_weekday_and_weekend() -> None:
    assert not is_weekend_date(date(2026, 7, 1))
    assert is_weekend_date(date(2026, 7, 4))


def test_is_weekend_trip_accepts_friday_to_sunday() -> None:
    assert is_weekend_trip(date(2026, 7, 3), date(2026, 7, 5))


def test_next_weekend_start_returns_same_saturday_or_next_one() -> None:
    assert next_weekend_start(date(2026, 7, 4)) == date(2026, 7, 4)
    assert next_weekend_start(date(2026, 7, 1)) == date(2026, 7, 4)

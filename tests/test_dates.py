from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from weekend_radar.dates import generate_weekend_windows, is_weekend_date, next_weekend_start
from weekend_radar.models import WeekendSearchRules

RIGA = ZoneInfo("Europe/Riga")


def test_is_weekend_date_distinguishes_weekday_and_weekend() -> None:
    assert not is_weekend_date(date(2026, 7, 1))
    assert is_weekend_date(date(2026, 7, 4))


def test_next_weekend_start_returns_same_saturday_or_next_one() -> None:
    assert next_weekend_start(date(2026, 7, 4)) == date(2026, 7, 4)
    assert next_weekend_start(date(2026, 7, 1)) == date(2026, 7, 4)


def test_generate_weekend_windows_when_today_is_monday() -> None:
    windows = generate_weekend_windows(
        current_at=datetime(2026, 7, 6, 9, 0, tzinfo=RIGA),
    )

    assert len(windows) == 8
    assert windows[0].depart_date == date(2026, 7, 10)
    assert windows[0].return_date == date(2026, 7, 12)
    assert windows[0].pattern_name == "friday_evening_to_sunday_evening"
    assert windows[0].preferred_outbound_start_time == time(hour=15)
    assert windows[0].preferred_return_end_time == time(hour=23)
    assert windows[0].nights == 2


def test_generate_weekend_windows_when_today_is_friday_morning_keeps_friday_evening() -> None:
    windows = generate_weekend_windows(
        current_at=datetime(2026, 7, 10, 10, 0, tzinfo=RIGA),
    )

    assert windows[0].pattern_name == "friday_evening_to_sunday_evening"
    assert windows[0].depart_date == date(2026, 7, 10)
    assert windows[1].pattern_name == "friday_evening_to_monday_morning"


def test_generate_weekend_windows_when_today_is_friday_evening_skips_passed_friday_windows() -> (
    None
):
    windows = generate_weekend_windows(
        current_at=datetime(2026, 7, 10, 23, 0, tzinfo=RIGA),
    )

    assert windows[0].pattern_name == "saturday_morning_to_sunday_evening"
    assert windows[0].depart_date == date(2026, 7, 11)
    assert all(window.depart_date >= date(2026, 7, 11) for window in windows)


def test_generate_weekend_windows_handles_end_of_month_rollover() -> None:
    windows = generate_weekend_windows(
        current_at=datetime(2026, 1, 30, 23, 30, tzinfo=RIGA),
    )

    assert windows[0].depart_date == date(2026, 1, 31)
    assert windows[0].return_date == date(2026, 2, 1)
    assert windows[1].return_date == date(2026, 2, 2)


def test_generate_weekend_windows_handles_end_of_year_rollover() -> None:
    windows = generate_weekend_windows(
        current_at=datetime(2026, 12, 31, 12, 0, tzinfo=RIGA),
    )

    assert windows[0].depart_date == date(2027, 1, 1)
    assert windows[0].return_date == date(2027, 1, 3)


def test_generate_weekend_windows_handles_dst_boundary_in_riga() -> None:
    windows = generate_weekend_windows(
        current_at=datetime(2026, 3, 27, 14, 0, tzinfo=RIGA),
    )

    assert windows[0].depart_date == date(2026, 3, 27)
    assert windows[0].return_date == date(2026, 3, 29)
    assert windows[1].return_date == date(2026, 3, 30)


def test_generate_weekend_windows_respects_injected_rules_count() -> None:
    windows = generate_weekend_windows(
        current_at=datetime(2026, 7, 6, 9, 0, tzinfo=RIGA),
        rules=WeekendSearchRules(future_windows_count=3),
    )

    assert len(windows) == 3


def test_generate_weekend_windows_rejects_naive_current_time() -> None:
    with pytest.raises(ValueError):
        generate_weekend_windows(current_at=datetime(2026, 7, 6, 9, 0))

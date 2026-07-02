"""Small date helpers for weekend-oriented logic."""

from __future__ import annotations

from datetime import date, timedelta


def is_weekend_date(value: date) -> bool:
    """Return True for Saturday and Sunday."""

    return value.weekday() >= 5


def is_weekend_trip(depart_date: date, return_date: date) -> bool:
    """Return True when a trip starts on Friday/Saturday and returns on Sunday/Monday."""

    departure_ok = depart_date.weekday() in {4, 5}
    return_ok = return_date.weekday() in {6, 0}
    return departure_ok and return_ok and return_date >= depart_date


def next_weekend_start(from_date: date) -> date:
    """Return the next Saturday on or after the provided date."""

    offset = (5 - from_date.weekday()) % 7
    return from_date + timedelta(days=offset)

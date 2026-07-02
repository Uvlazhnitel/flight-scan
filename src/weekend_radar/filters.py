"""Filtering helpers for destinations and placeholder flight options."""

from __future__ import annotations

from collections.abc import Iterable

from weekend_radar.models import Destination, FlightOffer, WeekendSearchRules


def enabled_destinations(destinations: Iterable[Destination]) -> list[Destination]:
    """Keep only enabled destinations."""

    return [destination for destination in destinations if destination.enabled]


def matches_weekend_rules(flight: FlightOffer, weekend_rules: WeekendSearchRules) -> bool:
    """Check whether a flight fits the configured weekend-trip rules."""

    nights = (flight.return_depart_at.date() - flight.depart_at.date()).days
    return any(
        (
            pattern_name == "friday_evening_to_sunday_evening"
            and flight.depart_at.weekday() == 4
            and flight.return_depart_at.weekday() == 6
            and nights == 2
        )
        or (
            pattern_name == "friday_evening_to_monday_morning"
            and flight.depart_at.weekday() == 4
            and flight.return_depart_at.weekday() == 0
            and nights == 3
        )
        or (
            pattern_name == "saturday_morning_to_sunday_evening"
            and flight.depart_at.weekday() == 5
            and flight.return_depart_at.weekday() == 6
            and nights == 1
        )
        or (
            pattern_name == "saturday_morning_to_monday_morning"
            and flight.depart_at.weekday() == 5
            and flight.return_depart_at.weekday() == 0
            and nights == 2
        )
        for pattern_name in weekend_rules.enabled_patterns
    )


def weekend_flights(
    flights: Iterable[FlightOffer],
    weekend_rules: WeekendSearchRules,
) -> list[FlightOffer]:
    """Keep only flights that match the configured weekend-trip rule."""

    return [flight for flight in flights if matches_weekend_rules(flight, weekend_rules)]

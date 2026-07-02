"""Filtering helpers for destinations and placeholder flight options."""

from __future__ import annotations

from collections.abc import Iterable

from weekend_radar.models import Destination, FlightOffer, WeekendWindow


def enabled_destinations(destinations: Iterable[Destination]) -> list[Destination]:
    """Keep only enabled destinations."""

    return [destination for destination in destinations if destination.enabled]


def matches_weekend_window(flight: FlightOffer, weekend_window: WeekendWindow) -> bool:
    """Check whether a flight fits the configured weekend-trip rules."""

    nights = (flight.return_depart_at.date() - flight.depart_at.date()).days
    return (
        flight.depart_at.weekday() in weekend_window.departure_weekdays
        and flight.return_depart_at.weekday() in weekend_window.return_weekdays
        and weekend_window.min_nights <= nights <= weekend_window.max_nights
    )


def weekend_flights(
    flights: Iterable[FlightOffer],
    weekend_window: WeekendWindow,
) -> list[FlightOffer]:
    """Keep only flights that match the configured weekend-trip rule."""

    return [flight for flight in flights if matches_weekend_window(flight, weekend_window)]

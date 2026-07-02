"""Filtering helpers for destinations and placeholder flight options."""

from __future__ import annotations

from collections.abc import Iterable

from weekend_radar.dates import is_weekend_trip
from weekend_radar.models import Destination, FlightOption


def enabled_destinations(destinations: Iterable[Destination]) -> list[Destination]:
    """Keep only enabled destinations."""

    return [destination for destination in destinations if destination.enabled]


def weekend_flights(flights: Iterable[FlightOption]) -> list[FlightOption]:
    """Keep only flights that match the simple weekend-trip rule."""

    return [flight for flight in flights if is_weekend_trip(flight.depart_date, flight.return_date)]

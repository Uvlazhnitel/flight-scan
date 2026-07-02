"""Filtering helpers for weekend flight offers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import time

from weekend_radar.models import (
    Destination,
    FlightOffer,
    OfferFilterRules,
    WeekendSearchRules,
    WeekendWindow,
)

LATEST_OUTBOUND_ARRIVAL = time(hour=0, minute=30)
EARLIEST_DEPARTURE = time(hour=6, minute=0)


def enabled_destinations(destinations: Iterable[Destination]) -> list[Destination]:
    """Keep only enabled destinations."""

    return [destination for destination in destinations if destination.enabled]


def is_destination_enabled(destination: Destination) -> bool:
    """Return True when a destination is enabled."""

    return destination.enabled


def is_within_price_limit(offer: FlightOffer, filter_rules: OfferFilterRules) -> bool:
    """Return True when the offer price does not exceed the configured maximum."""

    return offer.price_eur <= filter_rules.max_price_eur


def is_direct_enough(offer: FlightOffer, filter_rules: OfferFilterRules) -> bool:
    """Return True when stop-count rules allow the offer."""

    return not filter_rules.direct_only or offer.stops == 0


def has_valid_outbound_timing(offer: FlightOffer) -> bool:
    """Return True when outbound timing is practical for a weekend trip."""

    arrival_time = offer.arrive_at.timetz().replace(tzinfo=None)
    return offer.depart_at.timetz().replace(tzinfo=None) >= EARLIEST_DEPARTURE and (
        offer.arrive_at.date() == offer.depart_at.date() or arrival_time <= LATEST_OUTBOUND_ARRIVAL
    )


def has_valid_return_timing(offer: FlightOffer, weekend_window: WeekendWindow) -> bool:
    """Return True when return departure timing is practical for the trip pattern."""

    return_departure_time = offer.return_depart_at.timetz().replace(tzinfo=None)
    if weekend_window.pattern_name.endswith("monday_morning"):
        return True
    return return_departure_time >= EARLIEST_DEPARTURE


def has_valid_trip_duration(offer: FlightOffer) -> bool:
    """Return True when the trip spans a practical number of nights."""

    nights = (offer.return_depart_at.date() - offer.depart_at.date()).days
    return 1 <= nights <= 4


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


def is_useful_weekend_offer(
    offer: FlightOffer,
    destination: Destination,
    weekend_window: WeekendWindow,
    filter_rules: OfferFilterRules,
) -> bool:
    """Return True when an offer is practical enough to keep for later scoring."""

    return (
        is_destination_enabled(destination)
        and is_within_price_limit(offer, filter_rules)
        and is_direct_enough(offer, filter_rules)
        and has_valid_outbound_timing(offer)
        and has_valid_return_timing(offer, weekend_window)
        and has_valid_trip_duration(offer)
    )


def filter_useful_weekend_offers(
    offers: Iterable[FlightOffer],
    destination: Destination,
    weekend_window: WeekendWindow,
    filter_rules: OfferFilterRules,
) -> list[FlightOffer]:
    """Filter a list of offers down to useful weekend-trip candidates."""

    return [
        offer
        for offer in offers
        if is_useful_weekend_offer(offer, destination, weekend_window, filter_rules)
    ]

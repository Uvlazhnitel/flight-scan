"""Explainable scoring helpers for weekend flight deals."""

from __future__ import annotations

from datetime import time

from weekend_radar.models import DealCandidate, DealScore, Destination, FlightOffer, WeekendWindow

LATE_ARRIVAL_CUTOFF = time(hour=0, minute=30)
EARLY_DEPARTURE_CUTOFF = time(hour=6, minute=0)


def price_points(flight: FlightOffer) -> tuple[int, str | None]:
    """Return the positive price contribution and its human-readable reason."""

    if flight.price_eur <= 50:
        return 30, "Exceptional price at or below 50 EUR"
    if flight.price_eur <= 80:
        return 20, "Very good price at or below 80 EUR"
    if flight.price_eur <= 120:
        return 10, "Reasonable weekend price at or below 120 EUR"
    return 0, None


def direct_flight_points(flight: FlightOffer) -> tuple[int, str | None]:
    """Return the direct-flight bonus when applicable."""

    if flight.stops == 0:
        return 20, "Direct flight keeps the trip simple"
    return 0, None


def is_good_outbound_timing(flight: FlightOffer, weekend_window: WeekendWindow) -> bool:
    """Return True when outbound timing fits the preferred weekend window."""

    departure_time = flight.depart_at.timetz().replace(tzinfo=None)
    arrival_time = flight.arrive_at.timetz().replace(tzinfo=None)
    return (
        weekend_window.preferred_outbound_start_time
        <= departure_time
        <= weekend_window.preferred_outbound_end_time
        and weekend_window.preferred_outbound_start_time
        <= arrival_time
        <= weekend_window.preferred_outbound_end_time
    )


def is_good_return_timing(flight: FlightOffer, weekend_window: WeekendWindow) -> bool:
    """Return True when return departure fits the preferred weekend return window."""

    return_time = flight.return_depart_at.timetz().replace(tzinfo=None)
    return (
        weekend_window.preferred_return_start_time
        <= return_time
        <= weekend_window.preferred_return_end_time
    )


def nature_points(destination: Destination) -> tuple[int, str]:
    """Return the destination nature bonus scaled from a 0-10 input to a 0-15 range."""

    bonus = round(destination.nature_score * 1.5)
    return bonus, f"Destination nature appeal adds {bonus} points"


def late_arrival_penalty(flight: FlightOffer) -> tuple[int, str | None]:
    """Return the late-arrival penalty when outbound arrival is after 00:30 next day."""

    if flight.arrive_at.date() > flight.depart_at.date():
        arrival_time = flight.arrive_at.timetz().replace(tzinfo=None)
        if arrival_time > LATE_ARRIVAL_CUTOFF:
            return -20, "Late outbound arrival after 00:30"
    return 0, None


def early_departure_penalty(flight: FlightOffer) -> tuple[int, str | None]:
    """Return the early-departure penalty when outbound leaves before 06:00."""

    if flight.depart_at.timetz().replace(tzinfo=None) < EARLY_DEPARTURE_CUTOFF:
        return -15, "Outbound departure is before 06:00"
    return 0, None


def one_stop_penalty(flight: FlightOffer) -> tuple[int, str | None]:
    """Return the one-stop penalty when exactly one stop is present."""

    if flight.stops == 1:
        return -15, "One-stop itinerary adds travel friction"
    return 0, None


def score_offer(
    flight: FlightOffer,
    destination: Destination,
    weekend_window: WeekendWindow,
) -> DealScore:
    """Return an explainable score with ordered reasons and warnings."""

    total_score = 0
    reasons: list[str] = []
    warnings: list[str] = []

    price_score, price_reason = price_points(flight)
    total_score += price_score
    if price_reason:
        reasons.append(price_reason)

    direct_score, direct_reason = direct_flight_points(flight)
    total_score += direct_score
    if direct_reason:
        reasons.append(direct_reason)

    if is_good_outbound_timing(flight, weekend_window):
        total_score += 15
        reasons.append("Outbound timing fits the preferred weekend window")

    if is_good_return_timing(flight, weekend_window):
        total_score += 15
        reasons.append("Return timing fits the preferred weekend window")

    nature_bonus, nature_reason = nature_points(destination)
    total_score += nature_bonus
    if nature_bonus > 0:
        reasons.append(nature_reason)

    for penalty_fn in (late_arrival_penalty, early_departure_penalty, one_stop_penalty):
        penalty, warning = penalty_fn(flight)
        total_score += penalty
        if warning:
            warnings.append(warning)

    return DealScore(total_score=total_score, reasons=reasons, warnings=warnings)


def build_deal_candidate(
    flight: FlightOffer,
    destination: Destination,
    weekend_window: WeekendWindow,
) -> DealCandidate:
    """Build a scored deal candidate for an already-filtered offer."""

    return DealCandidate(
        offer=flight,
        destination=destination,
        score=score_offer(flight, destination, weekend_window),
    )

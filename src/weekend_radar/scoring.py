"""Deterministic placeholder scoring helpers for deals."""

from __future__ import annotations

from weekend_radar.models import Destination, FlightOption


def qualifies_price(flight: FlightOption, destination: Destination) -> bool:
    """Check whether a flight price meets the configured threshold."""

    return flight.total_price_eur <= destination.threshold_eur


def score_flight(flight: FlightOption, destination: Destination) -> int:
    """Return a simple positive score where cheaper flights rank higher."""

    margin = destination.threshold_eur - flight.total_price_eur
    return max(0, margin)

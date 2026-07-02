"""Deterministic placeholder scoring helpers for deals."""

from __future__ import annotations

from weekend_radar.models import AppConfig, DealCandidate, DealScore, Destination, FlightOffer


def threshold_for_destination(destination: Destination, app_config: AppConfig) -> int:
    """Get the configured threshold for a destination code with global fallback."""

    return app_config.destination_thresholds_eur.get(
        destination.code,
        app_config.default_price_threshold_eur,
    )


def qualifies_price(flight: FlightOffer, destination: Destination, app_config: AppConfig) -> bool:
    """Check whether a flight price meets the configured threshold."""

    return flight.price_eur <= threshold_for_destination(destination, app_config)


def score_flight(
    flight: FlightOffer,
    destination: Destination,
    app_config: AppConfig,
) -> DealScore:
    """Return a transparent score for a qualifying or near-qualifying flight."""

    threshold = threshold_for_destination(destination, app_config)
    price_margin = max(0, threshold - flight.price_eur)
    destination_bonus = destination.nature_score
    return DealScore(
        threshold_eur=threshold,
        price_margin_eur=price_margin,
        destination_bonus=destination_bonus,
        total_score=price_margin + destination_bonus,
    )


def build_deal_candidate(
    flight: FlightOffer,
    destination: Destination,
    app_config: AppConfig,
) -> DealCandidate | None:
    """Build a deal candidate for qualifying offers only."""

    if not qualifies_price(flight, destination, app_config):
        return None
    return DealCandidate(
        offer=flight,
        destination=destination,
        score=score_flight(flight, destination, app_config),
    )

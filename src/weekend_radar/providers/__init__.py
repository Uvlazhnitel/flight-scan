"""Provider boundaries for Weekend Radar."""

from weekend_radar.providers.base import FlightProvider
from weekend_radar.providers.mock import MockFlightProvider

__all__ = ["FlightProvider", "MockFlightProvider"]

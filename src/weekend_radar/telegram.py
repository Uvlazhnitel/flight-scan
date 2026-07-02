"""Telegram placeholder module for future notification work."""

from __future__ import annotations

from dataclasses import dataclass

from weekend_radar.models import FlightOption


@dataclass(slots=True)
class TelegramNotifier:
    """A no-network notifier placeholder for milestone one."""

    chat_id: str | None

    def format_message(self, flight: FlightOption) -> str:
        """Create a simple text summary for a future notification."""

        return (
            f"{flight.origin} -> {flight.destination} for {flight.total_price_eur} "
            f"{flight.currency} via {flight.provider}"
        )

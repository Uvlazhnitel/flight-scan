"""Telegram placeholder module for future notification work."""

from __future__ import annotations

from dataclasses import dataclass

from weekend_radar.models import DealCandidate, FlightOffer


@dataclass(slots=True)
class TelegramNotifier:
    """A no-network notifier placeholder for milestone one."""

    chat_id: str | None

    def format_message(self, flight: FlightOffer) -> str:
        """Create a simple text summary for a future notification."""

        return (
            f"{flight.origin} -> {flight.destination} for {flight.price_eur} "
            f"{flight.currency} via {flight.provider}"
        )

    def format_deal_candidate(self, candidate: DealCandidate) -> str:
        """Create a score-aware text summary for a scored deal candidate."""

        reasons = "; ".join(candidate.score.reasons) if candidate.score.reasons else "No highlights"
        warnings = (
            f" Warnings: {'; '.join(candidate.score.warnings)}" if candidate.score.warnings else ""
        )
        return (
            f"{self.format_message(candidate.offer)}. "
            f"Score: {candidate.score.total_score}. "
            f"Why it stands out: {reasons}.{warnings}"
        )

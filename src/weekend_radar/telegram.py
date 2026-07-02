"""Telegram notification formatting and sending helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from weekend_radar.models import DealCandidate, FlightOffer

TELEGRAM_API_BASE_URL = "https://api.telegram.org"


@dataclass(slots=True)
class TelegramNotifier:
    """Send deal notifications to Telegram or print them in dry-run mode."""

    chat_id: str | None
    bot_token: str | None = None
    dry_run: bool = True
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("weekend_radar.telegram")
    )

    def format_message(self, flight: FlightOffer) -> str:
        """Create a compact one-line summary for a raw flight offer."""

        return (
            f"{flight.origin} -> {flight.destination} for {flight.price_eur} "
            f"{flight.currency} via {flight.provider}"
        )

    def format_deal_candidate(self, candidate: DealCandidate) -> str:
        """Create a non-technical Telegram message for a scored weekend deal."""

        outbound = self._format_trip_segment(
            label="Outbound",
            depart_at=candidate.offer.depart_at,
            arrive_at=candidate.offer.arrive_at,
        )
        inbound = self._format_trip_segment(
            label="Return",
            depart_at=candidate.offer.return_depart_at,
            arrive_at=candidate.offer.return_arrive_at,
        )
        reasons = "\n".join(f"- {reason}" for reason in candidate.score.reasons)
        warnings = ""
        if candidate.score.warnings:
            warning_lines = "\n".join(f"- {warning}" for warning in candidate.score.warnings)
            warnings = f"\n\nWarnings:\n{warning_lines}"
        booking_line = ""
        if candidate.offer.booking_url:
            booking_line = f"\n\nBooking URL: {candidate.offer.booking_url}"

        return (
            "🔥 Weekend deal from Riga\n\n"
            f"Route: {candidate.offer.origin} -> {candidate.offer.destination} / "
            f"{candidate.destination.city}\n"
            f"Price found: EUR {candidate.offer.price_eur}\n"
            f"{outbound}\n"
            f"{inbound}\n"
            f"Score: {candidate.score.total_score}/100\n\n"
            f"Why it looks good:\n{reasons}"
            f"{warnings}"
            f"{booking_line}\n\n"
            "Note: verify the final price before booking."
        )

    def send_deal(self, candidate: DealCandidate) -> bool:
        """Send a deal notification or print it in dry-run mode."""

        message_text = self.format_deal_candidate(candidate)
        if self.dry_run:
            print(message_text)
            self.logger.info(
                "Dry-run Telegram notification printed for %s",
                candidate.offer.destination,
            )
            return True

        if not self.bot_token or not self.chat_id:
            self.logger.error(
                "Telegram send skipped because TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing"
            )
            return False

        try:
            response = httpx.post(
                f"{TELEGRAM_API_BASE_URL}/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message_text,
                },
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            self.logger.error("Telegram API request failed: %s", exc)
            return False

        if response.status_code >= 400:
            self.logger.error(
                "Telegram API returned HTTP %s: %s",
                response.status_code,
                response.text,
            )
            return False

        try:
            response_data = response.json()
        except ValueError as exc:
            self.logger.error("Telegram API returned invalid JSON: %s", exc)
            return False

        if not response_data.get("ok"):
            self.logger.error(
                "Telegram API reported failure: %s",
                response_data.get("description", "unknown error"),
            )
            return False

        self.logger.info("Telegram notification sent for %s", candidate.offer.destination)
        return True

    @staticmethod
    def _format_trip_segment(*, label: str, depart_at: datetime, arrive_at: datetime) -> str:
        """Format one readable trip segment for Telegram."""

        return (
            f"{label}: {depart_at.strftime('%a %d %b %H:%M')} -> "
            f"{arrive_at.strftime('%a %d %b %H:%M')}"
        )

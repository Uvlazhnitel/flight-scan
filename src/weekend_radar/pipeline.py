"""Pipeline orchestration for one complete Weekend Radar scan run."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from weekend_radar.config import AppSettings, load_app_config, load_settings
from weekend_radar.dates import generate_weekend_windows
from weekend_radar.db import DatabaseConfig, StateDatabase
from weekend_radar.filters import enabled_destinations, filter_useful_weekend_offers
from weekend_radar.models import Destination, FlightOffer, PipelineResult, WeekendWindow
from weekend_radar.providers.mock import MockFlightProvider
from weekend_radar.scoring import build_deal_candidate
from weekend_radar.telegram import TelegramNotifier

DEFAULT_ORIGIN = "RIX"
LOGGER = logging.getLogger("weekend_radar.pipeline")


async def _search_all_offers(
    *,
    provider: MockFlightProvider,
    origin: str,
    destinations: list[Destination],
    weekend_windows: list[WeekendWindow],
) -> list[tuple[Destination, WeekendWindow, list[FlightOffer]]]:
    """Fetch offers for every active destination and weekend window pair."""

    search_results = []
    for destination in destinations:
        for weekend_window in weekend_windows:
            offers = await provider.search_weekend_flights(origin, destination, weekend_window)
            search_results.append((destination, weekend_window, offers))
    return search_results


def run_pipeline(
    settings: AppSettings | None = None,
    *,
    current_at: datetime | None = None,
) -> PipelineResult:
    """Run one full mock-backed scan with SQLite persistence and deduplication."""

    app_settings = settings or load_settings()
    app_config = load_app_config(Path(app_settings.config_path))
    active_destinations = enabled_destinations(app_config.destinations)
    weekend_windows = generate_weekend_windows(
        current_at=current_at,
        rules=app_config.weekend_search,
    )
    database = StateDatabase(DatabaseConfig(path=app_settings.db_path))
    scan_started_at = current_at.astimezone(UTC) if current_at is not None else datetime.now(UTC)
    scan_run_id = database.start_scan_run(started_at=scan_started_at)
    provider = MockFlightProvider()
    notifier = TelegramNotifier(
        chat_id=app_settings.telegram_chat_id,
        bot_token=app_settings.telegram_bot_token,
        dry_run=app_settings.telegram_dry_run,
    )

    checked_offer_count = 0
    candidate_count = 0
    notified_count = 0
    skipped_duplicate_count = 0
    failed_notification_count = 0

    try:
        search_results = asyncio.run(
            _search_all_offers(
                provider=provider,
                origin=DEFAULT_ORIGIN,
                destinations=active_destinations,
                weekend_windows=weekend_windows,
            )
        )
        for destination, weekend_window, offers in search_results:
            checked_offer_count += len(offers)
            database.persist_checked_offers(offers, scan_run_id=scan_run_id)

            useful_offers = filter_useful_weekend_offers(
                offers,
                destination,
                weekend_window,
                app_config.offer_filters,
            )
            for offer in useful_offers:
                candidate = build_deal_candidate(offer, destination, weekend_window)
                candidate_count += 1
                decision = database.should_notify(candidate, evaluated_at=offer.checked_at)
                if decision.should_notify:
                    message_text = notifier.format_deal_candidate(candidate)
                    if notifier.send_deal(candidate):
                        database.record_notification(
                            candidate,
                            message_text=message_text,
                            scan_run_id=scan_run_id,
                            notified_at=offer.checked_at,
                        )
                        notified_count += 1
                    else:
                        failed_notification_count += 1
                        LOGGER.error(
                            "Notification failed for %s -> %s on %s",
                            offer.origin,
                            offer.destination,
                            offer.depart_at.date().isoformat(),
                        )
                else:
                    skipped_duplicate_count += 1
    finally:
        database.finish_scan_run(
            scan_run_id,
            status="ok",
            checked_offer_count=checked_offer_count,
            candidate_count=candidate_count,
            notified_count=notified_count,
            skipped_duplicate_count=skipped_duplicate_count,
            finished_at=scan_started_at,
        )
        database.close()

    return PipelineResult(
        status="ok",
        destination_count=len(active_destinations),
        weekend_window_count=len(weekend_windows),
        checked_offer_count=checked_offer_count,
        candidate_count=candidate_count,
        notified_count=notified_count,
        skipped_duplicate_count=skipped_duplicate_count,
        failed_notification_count=failed_notification_count,
        scan_run_id=scan_run_id,
        source=str(app_settings.config_path),
        message="Weekend Radar completed a mock scan with Telegram notification handling.",
    )

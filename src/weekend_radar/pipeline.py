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
from weekend_radar.models import (
    AppConfig,
    DealCandidate,
    Destination,
    FlightOffer,
    OfferFilterRules,
    PipelineResult,
    ScanOverrides,
    WeekendSearchRules,
    WeekendWindow,
)
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


def _apply_overrides(app_config: AppConfig, overrides: ScanOverrides | None) -> AppConfig:
    """Return a config copy with one-run CLI overrides applied."""

    if overrides is None:
        return app_config

    weekend_search = WeekendSearchRules.model_validate(app_config.weekend_search.model_dump())
    offer_filters = OfferFilterRules.model_validate(app_config.offer_filters.model_dump())

    if overrides.weeks is not None:
        weekend_search.future_windows_count = overrides.weeks
    if overrides.max_price is not None:
        offer_filters.max_price_eur = overrides.max_price
    if overrides.direct_only is not None:
        offer_filters.direct_only = overrides.direct_only

    return AppConfig.model_validate(
        {
            **app_config.model_dump(),
            "weekend_search": weekend_search.model_dump(),
            "offer_filters": offer_filters.model_dump(),
        }
    )


def _rank_candidates(candidates: list[DealCandidate]) -> list[DealCandidate]:
    """Sort scored candidates in a deterministic best-first order."""

    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score.total_score,
            candidate.offer.price_eur,
            candidate.offer.depart_at,
            candidate.offer.destination,
        ),
    )


def run_pipeline(
    settings: AppSettings | None = None,
    *,
    current_at: datetime | None = None,
    overrides: ScanOverrides | None = None,
) -> PipelineResult:
    """Run one full mock-backed scan with SQLite persistence and deduplication."""

    app_settings = settings or load_settings()
    base_config = load_app_config(Path(app_settings.config_path))
    app_config = _apply_overrides(base_config, overrides)
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
        dry_run=(
            overrides.dry_run
            if overrides is not None and overrides.dry_run is not None
            else app_settings.telegram_dry_run
        ),
    )

    checked_offer_count = 0
    candidate_count = 0
    selected_top_deal_count = 0
    notified_count = 0
    skipped_duplicate_count = 0
    failed_notification_count = 0
    all_candidates: list[DealCandidate] = []

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
                all_candidates.append(build_deal_candidate(offer, destination, weekend_window))

        candidate_count = len(all_candidates)
        ranked_candidates = _rank_candidates(all_candidates)
        limit = overrides.limit if overrides is not None else 10
        selected_candidates = ranked_candidates[:limit]
        selected_top_deal_count = len(selected_candidates)

        for candidate in selected_candidates:
            decision = database.should_notify(candidate, evaluated_at=candidate.offer.checked_at)
            if decision.should_notify:
                message_text = notifier.format_deal_candidate(candidate)
                if notifier.send_deal(candidate):
                    database.record_notification(
                        candidate,
                        message_text=message_text,
                        scan_run_id=scan_run_id,
                        notified_at=candidate.offer.checked_at,
                    )
                    notified_count += 1
                else:
                    failed_notification_count += 1
                    LOGGER.error(
                        "Notification failed for %s -> %s on %s",
                        candidate.offer.origin,
                        candidate.offer.destination,
                        candidate.offer.depart_at.date().isoformat(),
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
        selected_top_deal_count=selected_top_deal_count,
        notified_count=notified_count,
        skipped_duplicate_count=skipped_duplicate_count,
        failed_notification_count=failed_notification_count,
        scan_run_id=scan_run_id,
        db_path=str(app_settings.db_path),
        source=str(app_settings.config_path),
        message="Weekend Radar completed a full mock scan run.",
    )

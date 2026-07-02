"""Command-line entrypoint for Weekend Radar."""

from __future__ import annotations

import logging

from weekend_radar.config import load_settings
from weekend_radar.pipeline import run_pipeline


def configure_logging(level: str) -> None:
    """Configure basic application logging."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    """Run one full mock-backed pipeline scan and log the outcome."""

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("weekend_radar")

    result = run_pipeline(settings)
    logger.info(result.message)
    logger.info(
        "Loaded %s enabled destinations from %s",
        result.destination_count,
        result.source,
    )
    logger.info(
        (
            "Generated %s windows, checked %s offers, scored %s candidates, "
            "sent %s notifications, skipped %s duplicates"
        ),
        result.weekend_window_count,
        result.checked_offer_count,
        result.candidate_count,
        result.notified_count,
        result.skipped_duplicate_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line entrypoint for the Weekend Radar skeleton."""

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
    """Run the skeleton pipeline and log the result."""

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

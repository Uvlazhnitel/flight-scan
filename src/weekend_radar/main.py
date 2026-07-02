"""Command-line entrypoint for Weekend Radar."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import NoReturn

from weekend_radar.config import ConfigLoadError, load_settings, validate_settings
from weekend_radar.models import PipelineResult, ScanOverrides
from weekend_radar.pipeline import PipelineRunError, run_pipeline


def configure_logging(level: str) -> None:
    """Configure basic application logging."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for Weekend Radar."""

    parser = argparse.ArgumentParser(
        prog="weekend-radar",
        description=(
            "Scan weekend flight deals from Riga with the configured provider and either "
            "print or send notifications."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Run one full weekend-deal scan",
        description=(
            "Load YAML config, fetch flight offers from the configured provider, score the "
            "top deals, then print or send notifications."
        ),
    )
    scan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force local printing instead of real Telegram sends for this run.",
    )
    scan_parser.add_argument(
        "--max-price",
        type=int,
        help="Override the max acceptable price in EUR for this run.",
    )
    scan_parser.add_argument(
        "--weeks",
        type=int,
        help="Override how many upcoming weekend windows to generate.",
    )
    direct_group = scan_parser.add_mutually_exclusive_group()
    direct_group.add_argument(
        "--direct-only",
        action="store_true",
        help="Require direct flights for this run.",
    )
    direct_group.add_argument(
        "--allow-stops",
        action="store_true",
        help="Allow stopover flights for this run.",
    )
    scan_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Keep only the top N scored deals before duplicate checks (default: 10).",
    )

    return parser


def build_scan_overrides(args: argparse.Namespace) -> ScanOverrides:
    """Translate parsed CLI args into per-run pipeline overrides."""

    direct_only: bool | None = None
    if args.direct_only:
        direct_only = True
    elif args.allow_stops:
        direct_only = False

    return ScanOverrides(
        dry_run=True if args.dry_run else None,
        max_price=args.max_price,
        weeks=args.weeks,
        direct_only=direct_only,
        limit=args.limit,
    )


def print_scan_summary(result: PipelineResult) -> None:
    """Print a concise scan summary to stdout."""

    mode_label = "dry-run" if result.dry_run else "real Telegram send"
    provider_label = (
        f"{result.provider_name} (mock data)"
        if result.provider_name == "mock"
        else f"{result.provider_name} (live provider)"
    )

    print("\n=== Scan Summary ===")
    print(f"Status: {result.status}")
    print(f"Provider: {provider_label}")
    print(f"Mode: {mode_label}")
    print(f"Config: {result.source}")
    print(f"SQLite: {result.db_path}")
    print(f"Enabled destinations: {result.destination_count}")
    print(f"Weekend windows: {result.weekend_window_count}")
    print(f"Checked offers: {result.checked_offer_count}")
    print(f"Scored candidates: {result.candidate_count}")
    print(f"Selected top deals: {result.selected_top_deal_count}")
    print(f"Notifications sent: {result.notified_count}")
    print(f"Skipped duplicates: {result.skipped_duplicate_count}")
    print(f"Failed notifications: {result.failed_notification_count}")


def _exit_with_user_error(message: str) -> NoReturn:
    """Print a short user-facing error and exit with a non-zero code."""

    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    """Run the Weekend Radar CLI."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = load_settings()
        validate_settings(settings)
    except ConfigLoadError as exc:
        _exit_with_user_error(str(exc))

    configure_logging(settings.log_level)
    logger = logging.getLogger("weekend_radar")

    if args.command == "scan":
        try:
            overrides = build_scan_overrides(args)
            result = run_pipeline(settings, overrides=overrides)
        except (ConfigLoadError, PipelineRunError) as exc:
            logger.error("%s", exc)
            _exit_with_user_error(str(exc))
        except Exception:
            logger.exception("Unexpected scan failure")
            _exit_with_user_error("Unexpected scan failure. Check the logs above for details.")

        logger.info(result.message)
        print_scan_summary(result)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

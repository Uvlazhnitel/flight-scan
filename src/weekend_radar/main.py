"""Command-line entrypoint for Weekend Radar."""

from __future__ import annotations

import argparse
import logging

from weekend_radar.config import load_settings
from weekend_radar.models import ScanOverrides
from weekend_radar.pipeline import run_pipeline


def configure_logging(level: str) -> None:
    """Configure basic application logging."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for Weekend Radar."""

    parser = argparse.ArgumentParser(prog="weekend-radar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run one full weekend-deal scan")
    scan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print deal notifications instead of sending them to Telegram",
    )
    scan_parser.add_argument(
        "--max-price",
        type=int,
        help="Override the max acceptable price in EUR for this run",
    )
    scan_parser.add_argument(
        "--weeks",
        type=int,
        help="Override how many upcoming weekend windows to generate",
    )
    direct_group = scan_parser.add_mutually_exclusive_group()
    direct_group.add_argument(
        "--direct-only",
        action="store_true",
        help="Allow only direct flights for this run",
    )
    direct_group.add_argument(
        "--allow-stops",
        action="store_true",
        help="Allow flights with stops for this run",
    )
    scan_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Keep only the top N scored deals before notification checks",
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


def print_scan_summary(result) -> None:
    """Print a concise scan summary to stdout."""

    print("\n=== Scan Summary ===")
    print(f"Status: {result.status}")
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


def main() -> int:
    """Run the Weekend Radar CLI."""

    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("weekend_radar")

    if args.command == "scan":
        overrides = build_scan_overrides(args)
        result = run_pipeline(settings, overrides=overrides)
        logger.info(result.message)
        print_scan_summary(result)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

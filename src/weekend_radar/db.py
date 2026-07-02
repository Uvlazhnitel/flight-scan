"""SQLite persistence layer for checked offers and notification history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from weekend_radar.models import DealCandidate, FlightOffer

PRICE_DROP_THRESHOLD_EUR = 15
NOTIFICATION_EXPIRY_DAYS = 14


@dataclass(slots=True)
class DatabaseConfig:
    """Configuration for the local SQLite file used by Weekend Radar."""

    path: Path


@dataclass(slots=True)
class NotificationRecord:
    """The most recent stored notification for a stable deal key."""

    deal_key: str
    notified_price_eur: int
    notified_at: datetime
    provider: str
    origin: str
    destination: str
    depart_date: date
    return_date: date
    message_text: str | None


@dataclass(slots=True)
class NotificationDecision:
    """The duplicate-protection decision for a scored deal candidate."""

    should_notify: bool
    reason: str
    deal_key: str
    previous_notification: NotificationRecord | None = None


def build_deal_key(offer: FlightOffer) -> str:
    """Build a stable key for duplicate notification protection."""

    return (
        f"{offer.origin}|{offer.destination}|{offer.depart_at.date().isoformat()}|"
        f"{offer.return_depart_at.date().isoformat()}|{offer.provider}"
    )


class StateDatabase:
    """SQLite-backed storage for checked offers, scan runs, and notification history."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.config.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.config.path)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        """Create required SQLite tables and indexes if they do not exist yet."""

        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    checked_offer_count INTEGER NOT NULL DEFAULT 0,
                    candidate_count INTEGER NOT NULL DEFAULT 0,
                    notified_count INTEGER NOT NULL DEFAULT 0,
                    skipped_duplicate_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS flight_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL,
                    deal_key TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    depart_date TEXT NOT NULL,
                    return_date TEXT NOT NULL,
                    depart_at TEXT NOT NULL,
                    arrive_at TEXT NOT NULL,
                    return_depart_at TEXT NOT NULL,
                    return_arrive_at TEXT NOT NULL,
                    price_eur INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    airline TEXT,
                    stops INTEGER NOT NULL,
                    booking_url TEXT,
                    checked_at TEXT NOT NULL,
                    FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id)
                );

                CREATE TABLE IF NOT EXISTS notified_deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER,
                    deal_key TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    depart_date TEXT NOT NULL,
                    return_date TEXT NOT NULL,
                    notified_price_eur INTEGER NOT NULL,
                    notified_at TEXT NOT NULL,
                    message_text TEXT,
                    FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_flight_offers_deal_key
                ON flight_offers (deal_key);

                CREATE INDEX IF NOT EXISTS idx_notified_deals_deal_key_notified_at
                ON notified_deals (deal_key, notified_at DESC);
                """
            )

    def close(self) -> None:
        """Close the SQLite connection."""

        self.connection.close()

    def start_scan_run(self, started_at: datetime | None = None) -> int:
        """Create a new scan-run record and return its identifier."""

        started_timestamp = self._normalize_timestamp(started_at or datetime.now(UTC))
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO scan_runs (started_at, status)
                VALUES (?, ?)
                """,
                (started_timestamp, "running"),
            )
        return int(cursor.lastrowid)

    def finish_scan_run(
        self,
        scan_run_id: int,
        *,
        status: str,
        checked_offer_count: int,
        candidate_count: int,
        notified_count: int,
        skipped_duplicate_count: int,
        finished_at: datetime | None = None,
    ) -> None:
        """Mark a scan run complete and persist aggregate counters."""

        finished_timestamp = self._normalize_timestamp(finished_at or datetime.now(UTC))
        with self.connection:
            self.connection.execute(
                """
                UPDATE scan_runs
                SET finished_at = ?,
                    status = ?,
                    checked_offer_count = ?,
                    candidate_count = ?,
                    notified_count = ?,
                    skipped_duplicate_count = ?
                WHERE id = ?
                """,
                (
                    finished_timestamp,
                    status,
                    checked_offer_count,
                    candidate_count,
                    notified_count,
                    skipped_duplicate_count,
                    scan_run_id,
                ),
            )

    def persist_checked_offer(self, offer: FlightOffer, *, scan_run_id: int) -> None:
        """Store one checked flight offer in SQLite."""

        with self.connection:
            self.connection.execute(
                """
                INSERT INTO flight_offers (
                    scan_run_id,
                    deal_key,
                    provider,
                    origin,
                    destination,
                    depart_date,
                    return_date,
                    depart_at,
                    arrive_at,
                    return_depart_at,
                    return_arrive_at,
                    price_eur,
                    currency,
                    airline,
                    stops,
                    booking_url,
                    checked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_run_id,
                    build_deal_key(offer),
                    offer.provider,
                    offer.origin,
                    offer.destination,
                    offer.depart_at.date().isoformat(),
                    offer.return_depart_at.date().isoformat(),
                    self._normalize_timestamp(offer.depart_at),
                    self._normalize_timestamp(offer.arrive_at),
                    self._normalize_timestamp(offer.return_depart_at),
                    self._normalize_timestamp(offer.return_arrive_at),
                    offer.price_eur,
                    offer.currency,
                    offer.airline,
                    offer.stops,
                    offer.booking_url,
                    self._normalize_timestamp(offer.checked_at),
                ),
            )

    def persist_checked_offers(self, offers: list[FlightOffer], *, scan_run_id: int) -> None:
        """Store a batch of checked offers in SQLite."""

        for offer in offers:
            self.persist_checked_offer(offer, scan_run_id=scan_run_id)

    def get_latest_notification(self, deal_key: str) -> NotificationRecord | None:
        """Return the most recent notification record for a given deal key."""

        row = self.connection.execute(
            """
            SELECT
                deal_key,
                notified_price_eur,
                notified_at,
                provider,
                origin,
                destination,
                depart_date,
                return_date,
                message_text
            FROM notified_deals
            WHERE deal_key = ?
            ORDER BY notified_at DESC, id DESC
            LIMIT 1
            """,
            (deal_key,),
        ).fetchone()

        if row is None:
            return None

        return NotificationRecord(
            deal_key=row["deal_key"],
            notified_price_eur=row["notified_price_eur"],
            notified_at=datetime.fromisoformat(row["notified_at"]),
            provider=row["provider"],
            origin=row["origin"],
            destination=row["destination"],
            depart_date=date.fromisoformat(row["depart_date"]),
            return_date=date.fromisoformat(row["return_date"]),
            message_text=row["message_text"],
        )

    def should_notify(
        self,
        candidate: DealCandidate,
        *,
        evaluated_at: datetime | None = None,
    ) -> NotificationDecision:
        """Decide whether a scored deal should trigger a fresh notification."""

        deal_key = build_deal_key(candidate.offer)
        previous = self.get_latest_notification(deal_key)
        if previous is None:
            return NotificationDecision(
                should_notify=True,
                reason="first_notification",
                deal_key=deal_key,
            )

        evaluation_time = evaluated_at or candidate.offer.checked_at
        if previous.notified_price_eur - candidate.offer.price_eur >= PRICE_DROP_THRESHOLD_EUR:
            return NotificationDecision(
                should_notify=True,
                reason="price_drop",
                deal_key=deal_key,
                previous_notification=previous,
            )

        if evaluation_time - previous.notified_at > timedelta(days=NOTIFICATION_EXPIRY_DAYS):
            return NotificationDecision(
                should_notify=True,
                reason="stale_notification",
                deal_key=deal_key,
                previous_notification=previous,
            )

        return NotificationDecision(
            should_notify=False,
            reason="duplicate_recent_notification",
            deal_key=deal_key,
            previous_notification=previous,
        )

    def record_notification(
        self,
        candidate: DealCandidate,
        *,
        message_text: str,
        scan_run_id: int | None = None,
        notified_at: datetime | None = None,
    ) -> None:
        """Persist one successful notification event."""

        offer = candidate.offer
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO notified_deals (
                    scan_run_id,
                    deal_key,
                    provider,
                    origin,
                    destination,
                    depart_date,
                    return_date,
                    notified_price_eur,
                    notified_at,
                    message_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_run_id,
                    build_deal_key(offer),
                    offer.provider,
                    offer.origin,
                    offer.destination,
                    offer.depart_at.date().isoformat(),
                    offer.return_depart_at.date().isoformat(),
                    offer.price_eur,
                    self._normalize_timestamp(notified_at or offer.checked_at),
                    message_text,
                ),
            )

    @staticmethod
    def _normalize_timestamp(value: datetime) -> str:
        """Serialize a timezone-aware timestamp to ISO format."""

        return value.astimezone(UTC).isoformat()

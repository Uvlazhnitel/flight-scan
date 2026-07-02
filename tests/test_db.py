import sqlite3
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from weekend_radar.db import DatabaseConfig, StateDatabase, build_deal_key
from weekend_radar.models import Destination, FlightOffer, WeekendWindow
from weekend_radar.scoring import build_deal_candidate


def build_destination() -> Destination:
    return Destination(
        code="FCO",
        city="Rome",
        country="Italy",
        nature_score=4,
        enabled=True,
    )


def build_weekend_window() -> WeekendWindow:
    return WeekendWindow(
        depart_date=date(2026, 7, 10),
        return_date=date(2026, 7, 12),
        pattern_name="friday_evening_to_sunday_evening",
        preferred_outbound_start_time=time(15, 0),
        preferred_outbound_end_time=time(22, 30),
        preferred_return_start_time=time(15, 0),
        preferred_return_end_time=time(23, 0),
        nights=2,
    )


def build_offer(
    *,
    provider: str = "mock",
    depart_date: date = date(2026, 7, 10),
    return_date: date = date(2026, 7, 12),
    price_eur: int = 75,
    checked_at: datetime = datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
) -> FlightOffer:
    return FlightOffer(
        provider=provider,
        origin="RIX",
        destination="FCO",
        depart_at=datetime.combine(depart_date, time(17, 30), tzinfo=UTC),
        arrive_at=datetime.combine(depart_date, time(20, 5), tzinfo=UTC),
        return_depart_at=datetime.combine(return_date, time(18, 0), tzinfo=UTC),
        return_arrive_at=datetime.combine(return_date, time(20, 40), tzinfo=UTC),
        price_eur=price_eur,
        currency="EUR",
        airline="Air Baltic Mock",
        stops=0,
        booking_url="https://mock.example/offer",
        checked_at=checked_at,
    )


def build_candidate(offer: FlightOffer):
    return build_deal_candidate(offer, build_destination(), build_weekend_window())


def test_database_initializes_required_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "weekend_radar.sqlite3"

    database = StateDatabase(DatabaseConfig(path=database_path))
    database.close()

    connection = sqlite3.connect(database_path)
    try:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert "scan_runs" in table_names
    assert "flight_offers" in table_names
    assert "notified_deals" in table_names


def test_persist_checked_offers_and_finish_scan_run(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    offer = build_offer()

    scan_run_id = database.start_scan_run(started_at=offer.checked_at)
    database.persist_checked_offers([offer], scan_run_id=scan_run_id)
    database.finish_scan_run(
        scan_run_id,
        status="ok",
        checked_offer_count=1,
        candidate_count=1,
        notified_count=1,
        skipped_duplicate_count=0,
        finished_at=offer.checked_at,
    )

    flight_offer_rows = database.connection.execute(
        "SELECT COUNT(*) FROM flight_offers"
    ).fetchone()[0]
    scan_run_row = database.connection.execute(
        """
        SELECT status, checked_offer_count, candidate_count, notified_count, skipped_duplicate_count
        FROM scan_runs
        WHERE id = ?
        """,
        (scan_run_id,),
    ).fetchone()
    database.close()

    assert flight_offer_rows == 1
    assert tuple(scan_run_row) == ("ok", 1, 1, 1, 0)


def test_first_seen_deal_should_notify(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    candidate = build_candidate(build_offer())

    decision = database.should_notify(candidate)
    database.close()

    assert decision.should_notify is True
    assert decision.reason == "first_notification"
    assert decision.deal_key == build_deal_key(candidate.offer)


def test_same_key_without_large_price_drop_is_suppressed(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    initial_candidate = build_candidate(build_offer(price_eur=80))
    database.record_notification(
        initial_candidate,
        message_text="First alert",
        notified_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    follow_up = build_candidate(
        build_offer(
            price_eur=71,
            checked_at=datetime(2026, 7, 5, 9, 0, tzinfo=UTC),
        )
    )
    decision = database.should_notify(follow_up)
    database.close()

    assert decision.should_notify is False
    assert decision.reason == "duplicate_recent_notification"


def test_price_drop_of_fifteen_eur_triggers_new_notification(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    initial_candidate = build_candidate(build_offer(price_eur=80))
    database.record_notification(
        initial_candidate,
        message_text="First alert",
        notified_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    cheaper_candidate = build_candidate(
        build_offer(
            price_eur=65,
            checked_at=datetime(2026, 7, 5, 9, 0, tzinfo=UTC),
        )
    )
    decision = database.should_notify(cheaper_candidate)
    database.close()

    assert decision.should_notify is True
    assert decision.reason == "price_drop"


def test_notification_older_than_fourteen_days_can_notify_again(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    initial_candidate = build_candidate(build_offer(price_eur=80))
    notified_at = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    database.record_notification(
        initial_candidate,
        message_text="First alert",
        notified_at=notified_at,
    )

    later_candidate = build_candidate(
        build_offer(
            price_eur=80,
            checked_at=notified_at + timedelta(days=15),
        )
    )
    decision = database.should_notify(later_candidate)
    database.close()

    assert decision.should_notify is True
    assert decision.reason == "stale_notification"


def test_different_provider_does_not_collide(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    first_candidate = build_candidate(build_offer(provider="mock"))
    database.record_notification(
        first_candidate,
        message_text="First alert",
        notified_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    second_candidate = build_candidate(build_offer(provider="other_mock"))
    decision = database.should_notify(second_candidate)
    database.close()

    assert decision.should_notify is True
    assert decision.reason == "first_notification"


def test_different_dates_do_not_collide(tmp_path: Path) -> None:
    database = StateDatabase(DatabaseConfig(path=tmp_path / "weekend_radar.sqlite3"))
    first_candidate = build_candidate(build_offer())
    database.record_notification(
        first_candidate,
        message_text="First alert",
        notified_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    second_candidate = build_candidate(
        build_offer(
            depart_date=date(2026, 7, 17),
            return_date=date(2026, 7, 19),
            checked_at=datetime(2026, 7, 8, 9, 0, tzinfo=UTC),
        )
    )
    decision = database.should_notify(second_candidate)
    database.close()

    assert decision.should_notify is True
    assert decision.reason == "first_notification"

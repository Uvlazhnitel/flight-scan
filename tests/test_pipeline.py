import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from weekend_radar.config import AppSettings
from weekend_radar.dates import generate_weekend_windows
from weekend_radar.main import main
from weekend_radar.models import Destination, FlightOffer
from weekend_radar.pipeline import run_pipeline
from weekend_radar.providers.mock import MockFlightProvider

RIGA = ZoneInfo("Europe/Riga")


def test_run_pipeline_persists_offers_and_suppresses_duplicates(tmp_path: Path) -> None:
    config_path = tmp_path / "destinations.yaml"
    config_path.write_text(
        """
default_price_threshold_eur: 140
destination_thresholds_eur:
  FCO: 120
weekend_search:
  timezone: Europe/Riga
  future_windows_count: 8
  enabled_patterns:
    - friday_evening_to_sunday_evening
    - friday_evening_to_monday_morning
    - saturday_morning_to_sunday_evening
    - saturday_morning_to_monday_morning
offer_filters:
  max_price_eur: 120
  direct_only: true
destinations:
  - code: FCO
    city: Rome
    country: Italy
    nature_score: 3
    enabled: true
""".strip(),
        encoding="utf-8",
    )

    settings = AppSettings(
        config_path=config_path,
        db_path=tmp_path / "weekend_radar.sqlite3",
        log_level="INFO",
    )
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    first_result = run_pipeline(settings, current_at=current_at)
    second_result = run_pipeline(settings, current_at=current_at)

    assert first_result.status == "ok"
    assert first_result.destination_count == 1
    assert first_result.weekend_window_count == 8
    assert first_result.checked_offer_count == 48
    assert first_result.candidate_count == 24
    assert first_result.notified_count == 8
    assert first_result.skipped_duplicate_count == 16
    assert first_result.source == str(config_path)

    assert second_result.status == "ok"
    assert second_result.checked_offer_count == 48
    assert second_result.candidate_count == 24
    assert second_result.notified_count == 0
    assert second_result.skipped_duplicate_count == 24

    connection = sqlite3.connect(settings.db_path)
    try:
        flight_offer_rows = connection.execute("SELECT COUNT(*) FROM flight_offers").fetchone()[0]
        notified_rows = connection.execute("SELECT COUNT(*) FROM notified_deals").fetchone()[0]
        scan_run_rows = connection.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]
    finally:
        connection.close()

    assert flight_offer_rows == 96
    assert notified_rows == 8
    assert scan_run_rows == 2


def test_main_returns_success_with_sample_data(monkeypatch: object) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main() == 0


def test_mock_provider_returns_flight_offer_models() -> None:
    provider = MockFlightProvider()
    weekend_window = generate_weekend_windows(current_at=datetime(2026, 7, 6, 12, 0, tzinfo=RIGA))[
        0
    ]
    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=Destination(
                code="FCO",
                city="Rome",
                country="Italy",
                nature_score=3,
            ),
            weekend_window=weekend_window,
        )
    )

    assert offers
    assert all(isinstance(offer, FlightOffer) for offer in offers)

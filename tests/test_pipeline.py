import asyncio
from pathlib import Path

from weekend_radar.config import AppSettings
from weekend_radar.dates import generate_weekend_windows
from weekend_radar.main import main
from weekend_radar.models import Destination, FlightOffer
from weekend_radar.pipeline import run_pipeline
from weekend_radar.providers.mock import MockFlightProvider


def test_run_pipeline_loads_enabled_destinations_from_yaml(tmp_path: Path) -> None:
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
destinations:
  - code: FCO
    city: Rome
    country: Italy
    nature_score: 3
    enabled: true
  - code: BCN
    city: Barcelona
    country: Spain
    nature_score: 4
    enabled: false
""".strip(),
        encoding="utf-8",
    )

    settings = AppSettings(
        config_path=config_path,
        db_path=tmp_path / "weekend_radar.sqlite3",
        log_level="INFO",
    )

    result = run_pipeline(settings)

    assert result.status == "ok"
    assert result.destination_count == 1
    assert result.source == str(config_path)


def test_main_returns_success_with_sample_data(monkeypatch: object) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main() == 0


def test_mock_provider_returns_flight_offer_models() -> None:
    provider = MockFlightProvider()
    weekend_window = generate_weekend_windows()[0]
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

import asyncio
import json
import sqlite3
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from weekend_radar.config import AppSettings
from weekend_radar.dates import generate_weekend_windows
from weekend_radar.main import main
from weekend_radar.models import Destination, FlightOffer, ScanOverrides
from weekend_radar.pipeline import PipelineRunError, run_pipeline
from weekend_radar.providers.mock import MockFlightProvider

RIGA = ZoneInfo("Europe/Riga")
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def write_config(path: Path, *, provider: str = "mock") -> None:
    path.write_text(
        f"""
provider: {provider}
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


def build_settings(
    tmp_path: Path,
    *,
    dry_run: bool = True,
    provider: str = "mock",
    amadeus_api_key: str | None = "amadeus-key",
    amadeus_api_secret: str | None = "amadeus-secret",
) -> AppSettings:
    config_path = tmp_path / "destinations.yaml"
    write_config(config_path, provider=provider)
    return AppSettings(
        config_path=config_path,
        db_path=tmp_path / "weekend_radar.sqlite3",
        log_level="INFO",
        telegram_dry_run=dry_run,
        telegram_bot_token="secret-token",
        telegram_chat_id="12345",
        amadeus_api_key=amadeus_api_key,
        amadeus_api_secret=amadeus_api_secret,
    )


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def build_good_offer(
    *,
    price_eur: int,
    checked_at: datetime,
) -> FlightOffer:
    return FlightOffer(
        provider="mock",
        origin="RIX",
        destination="FCO",
        depart_at=datetime.combine(date(2026, 7, 10), time(17, 30), tzinfo=UTC),
        arrive_at=datetime.combine(date(2026, 7, 10), time(20, 10), tzinfo=UTC),
        return_depart_at=datetime.combine(date(2026, 7, 12), time(18, 25), tzinfo=UTC),
        return_arrive_at=datetime.combine(date(2026, 7, 12), time(21, 0), tzinfo=UTC),
        price_eur=price_eur,
        currency="EUR",
        airline="Air Baltic Mock",
        stops=0,
        booking_url="https://mock.example/book/fco",
        checked_at=checked_at,
    )


def test_run_pipeline_dry_run_records_notifications(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    first_result = run_pipeline(settings, current_at=current_at)
    second_result = run_pipeline(settings, current_at=current_at)

    assert first_result.status == "ok"
    assert first_result.destination_count == 1
    assert first_result.weekend_window_count == 8
    assert first_result.checked_offer_count == 48
    assert first_result.candidate_count == 24
    assert first_result.selected_top_deal_count == 10
    assert first_result.notified_count == 6
    assert first_result.skipped_duplicate_count == 4
    assert first_result.failed_notification_count == 0

    assert second_result.status == "ok"
    assert second_result.selected_top_deal_count == 10
    assert second_result.notified_count == 0
    assert second_result.skipped_duplicate_count == 10
    assert second_result.failed_notification_count == 0

    connection = sqlite3.connect(settings.db_path)
    try:
        flight_offer_rows = connection.execute("SELECT COUNT(*) FROM flight_offers").fetchone()[0]
        notified_rows = connection.execute("SELECT COUNT(*) FROM notified_deals").fetchone()[0]
        scan_run_rows = connection.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]
    finally:
        connection.close()

    assert flight_offer_rows == 96
    assert notified_rows == 6
    assert scan_run_rows == 2


def test_run_pipeline_max_price_override_tightens_filtering(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    default_result = run_pipeline(settings, current_at=current_at)
    strict_result = run_pipeline(
        settings,
        current_at=current_at,
        overrides=ScanOverrides(dry_run=True, max_price=55, limit=10),
    )

    assert strict_result.candidate_count < default_result.candidate_count


def test_run_pipeline_weeks_override_changes_window_count(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    result = run_pipeline(
        settings,
        current_at=current_at,
        overrides=ScanOverrides(dry_run=True, weeks=4, limit=10),
    )

    assert result.weekend_window_count == 4


def test_run_pipeline_allow_stops_increases_candidate_pool(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    default_result = run_pipeline(settings, current_at=current_at)
    allow_stops_result = run_pipeline(
        settings,
        current_at=current_at,
        overrides=ScanOverrides(dry_run=True, direct_only=False, limit=10),
    )

    assert allow_stops_result.candidate_count > default_result.candidate_count


def test_run_pipeline_limit_keeps_only_top_n(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    result = run_pipeline(
        settings,
        current_at=current_at,
        overrides=ScanOverrides(dry_run=True, limit=5),
    )

    assert result.candidate_count == 24
    assert result.selected_top_deal_count == 5
    assert (
        result.notified_count + result.skipped_duplicate_count + result.failed_notification_count
        == 5
    )


def test_run_pipeline_continues_when_telegram_send_fails(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = build_settings(tmp_path, dry_run=False)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(500, text="server error", request=request)

    monkeypatch.setattr("weekend_radar.telegram.httpx.post", fake_post)

    result = run_pipeline(settings, current_at=current_at)

    assert result.status == "ok"
    assert result.checked_offer_count == 48
    assert result.candidate_count == 24
    assert result.selected_top_deal_count == 10
    assert result.notified_count == 0
    assert result.skipped_duplicate_count == 0
    assert result.failed_notification_count == 10

    connection = sqlite3.connect(settings.db_path)
    try:
        notified_rows = connection.execute("SELECT COUNT(*) FROM notified_deals").fetchone()[0]
    finally:
        connection.close()

    assert notified_rows == 0


def test_run_pipeline_marks_scan_failed_when_provider_raises(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    async def fake_search_weekend_flights(*args: object, **kwargs: object) -> list[FlightOffer]:
        raise RuntimeError("provider down")

    monkeypatch.setattr(
        "weekend_radar.providers.mock.MockFlightProvider.search_weekend_flights",
        fake_search_weekend_flights,
    )

    with pytest.raises(PipelineRunError):
        run_pipeline(settings, current_at=current_at)

    connection = sqlite3.connect(settings.db_path)
    try:
        scan_status = connection.execute(
            "SELECT status FROM scan_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
    finally:
        connection.close()

    assert scan_status == "failed"


def test_run_pipeline_fails_cleanly_when_real_send_lacks_credentials(tmp_path: Path) -> None:
    config_path = tmp_path / "destinations.yaml"
    write_config(config_path, provider="mock")
    settings = AppSettings(
        config_path=config_path,
        db_path=tmp_path / "weekend_radar.sqlite3",
        log_level="INFO",
        telegram_dry_run=False,
        telegram_bot_token=None,
        telegram_chat_id=None,
    )

    with pytest.raises(PipelineRunError) as exc_info:
        run_pipeline(settings)

    assert "requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID" in str(exc_info.value)


def test_run_pipeline_fails_cleanly_when_amadeus_credentials_are_missing(tmp_path: Path) -> None:
    settings = build_settings(
        tmp_path,
        provider="amadeus",
        amadeus_api_key=None,
        amadeus_api_secret=None,
    )

    with pytest.raises(PipelineRunError) as exc_info:
        run_pipeline(settings)

    assert "AMADEUS_API_KEY and AMADEUS_API_SECRET" in str(exc_info.value)


def test_run_pipeline_supports_amadeus_provider_with_mocked_http(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = build_settings(tmp_path, dry_run=True, provider="amadeus")
    current_at = datetime(2026, 7, 6, 12, 0, tzinfo=RIGA)

    async def fake_request(
        self: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        request = self.build_request(method, url, **kwargs)
        if url == "/v1/security/oauth2/token":
            return httpx.Response(
                200,
                json={"access_token": "token-123", "expires_in": 1800},
                request=request,
            )
        if url == "/v2/shopping/flight-offers":
            return httpx.Response(
                200,
                json=load_fixture("amadeus_flight_offers.json"),
                request=request,
            )
        raise AssertionError(f"Unexpected Amadeus path: {url}")

    monkeypatch.setattr("weekend_radar.providers.amadeus.httpx.AsyncClient.request", fake_request)

    result = run_pipeline(
        settings,
        current_at=current_at,
        overrides=ScanOverrides(dry_run=True, weeks=1, limit=10),
    )

    assert result.status == "ok"
    assert result.provider_name == "amadeus"
    assert result.checked_offer_count == 2
    assert result.candidate_count == 1
    assert result.notified_count == 1
    assert result.failed_notification_count == 0


def test_run_pipeline_price_drop_reenables_notification(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = build_settings(tmp_path, dry_run=True)
    first_checked_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    second_checked_at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    offers_by_call = [
        [build_good_offer(price_eur=80, checked_at=first_checked_at)],
        [build_good_offer(price_eur=65, checked_at=second_checked_at)],
    ]

    async def fake_search_weekend_flights(*args: object, **kwargs: object) -> list[FlightOffer]:
        return offers_by_call.pop(0)

    monkeypatch.setattr(
        "weekend_radar.providers.mock.MockFlightProvider.search_weekend_flights",
        fake_search_weekend_flights,
    )

    first_result = run_pipeline(
        settings,
        current_at=datetime(2026, 7, 6, 12, 0, tzinfo=RIGA),
        overrides=ScanOverrides(dry_run=True, weeks=1, limit=1),
    )
    second_result = run_pipeline(
        settings,
        current_at=datetime(2026, 7, 7, 12, 0, tzinfo=RIGA),
        overrides=ScanOverrides(dry_run=True, weeks=1, limit=1),
    )

    assert first_result.notified_count == 1
    assert second_result.notified_count == 1
    assert second_result.skipped_duplicate_count == 0

    connection = sqlite3.connect(settings.db_path)
    try:
        notified_rows = connection.execute(
            "SELECT notified_price_eur FROM notified_deals ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    assert [row[0] for row in notified_rows] == [80, 65]


def test_main_returns_success_with_sample_data(monkeypatch: object) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    monkeypatch.setenv("WEEKEND_RADAR_TELEGRAM_DRY_RUN", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "plain-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "plain-chat")
    monkeypatch.setenv("WEEKEND_RADAR_DB_PATH", "data/test-cli.sqlite3")
    monkeypatch.setattr(
        "sys.argv",
        ["weekend-radar", "scan", "--dry-run", "--limit", "3"],
    )

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

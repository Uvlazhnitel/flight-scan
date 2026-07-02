from datetime import UTC, date, datetime, time

import httpx

from weekend_radar.models import Destination, FlightOffer, WeekendWindow
from weekend_radar.scoring import build_deal_candidate
from weekend_radar.telegram import TelegramNotifier


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


def build_destination() -> Destination:
    return Destination(
        code="BGY",
        city="Bergamo",
        country="Italy",
        nature_score=8,
    )


def build_offer(*, booking_url: str | None = "https://mock.example/book") -> FlightOffer:
    return FlightOffer(
        provider="mock",
        origin="RIX",
        destination="BGY",
        depart_at=datetime(2026, 7, 10, 18, 40, tzinfo=UTC),
        arrive_at=datetime(2026, 7, 10, 21, 10, tzinfo=UTC),
        return_depart_at=datetime(2026, 7, 12, 18, 0, tzinfo=UTC),
        return_arrive_at=datetime(2026, 7, 12, 21, 10, tzinfo=UTC),
        price_eur=48,
        currency="EUR",
        airline="Air Baltic Mock",
        stops=0,
        booking_url=booking_url,
        checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )


def build_candidate(*, booking_url: str | None = "https://mock.example/book"):
    return build_deal_candidate(
        build_offer(booking_url=booking_url),
        build_destination(),
        build_weekend_window(),
    )


def test_dry_run_prints_message_and_reports_success(capsys: object) -> None:
    notifier = TelegramNotifier(chat_id=None, dry_run=True)

    result = notifier.send_deal(build_candidate())

    captured = capsys.readouterr()
    assert result is True
    assert "🔥 Weekend deal from Riga" in captured.out
    assert "Route: RIX -> BGY / Bergamo" in captured.out


def test_real_send_posts_expected_payload(monkeypatch: object) -> None:
    captured_request: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["timeout"] = timeout
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}}, request=request)

    monkeypatch.setattr("weekend_radar.telegram.httpx.post", fake_post)
    notifier = TelegramNotifier(chat_id="12345", bot_token="secret-token", dry_run=False)

    result = notifier.send_deal(build_candidate())

    assert result is True
    assert captured_request["url"] == "https://api.telegram.org/botsecret-token/sendMessage"
    assert captured_request["timeout"] == 10.0
    assert captured_request["json"]["chat_id"] == "12345"
    assert "Score: 92/100" in captured_request["json"]["text"]


def test_formatted_message_omits_warnings_section_when_empty() -> None:
    notifier = TelegramNotifier(chat_id="demo")

    message = notifier.format_deal_candidate(build_candidate())

    assert "Warnings:" not in message
    assert "Booking URL: https://mock.example/book" in message
    assert "Note: verify the final price before booking." in message


def test_real_send_logs_api_failure_and_returns_false(
    monkeypatch: object,
    caplog: object,
) -> None:
    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(500, text="server error", request=request)

    monkeypatch.setattr("weekend_radar.telegram.httpx.post", fake_post)
    notifier = TelegramNotifier(chat_id="12345", bot_token="secret-token", dry_run=False)

    result = notifier.send_deal(build_candidate())

    assert result is False
    assert "Telegram API returned HTTP 500" in caplog.text


def test_real_send_catches_httpx_exception(monkeypatch: object, caplog: object) -> None:
    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=httpx.Request("POST", url))

    monkeypatch.setattr("weekend_radar.telegram.httpx.post", fake_post)
    notifier = TelegramNotifier(chat_id="12345", bot_token="secret-token", dry_run=False)

    result = notifier.send_deal(build_candidate())

    assert result is False
    assert "Telegram API request failed" in caplog.text


def test_real_send_handles_api_ok_false(monkeypatch: object, caplog: object) -> None:
    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"ok": False, "description": "chat not found"},
            request=request,
        )

    monkeypatch.setattr("weekend_radar.telegram.httpx.post", fake_post)
    notifier = TelegramNotifier(chat_id="12345", bot_token="secret-token", dry_run=False)

    result = notifier.send_deal(build_candidate(booking_url=None))

    assert result is False
    assert "Telegram API reported failure: chat not found" in caplog.text

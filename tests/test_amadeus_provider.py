import asyncio
import json
from datetime import UTC, date, datetime, time
from pathlib import Path

import httpx
import pytest

from weekend_radar.models import Destination, FlightOffer, WeekendWindow
from weekend_radar.providers.amadeus import AmadeusFlightProvider
from weekend_radar.providers.base import ProviderError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def build_destination() -> Destination:
    return Destination(
        code="BGY",
        city="Bergamo",
        country="Italy",
        nature_score=6,
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


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_amadeus_provider_builds_expected_requests_and_normalizes_offers() -> None:
    requests: list[httpx.Request] = []
    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/security/oauth2/token":
            return httpx.Response(
                200,
                json={"access_token": "token-123", "expires_in": 1800},
                request=request,
            )
        if request.url.path == "/v2/shopping/flight-offers":
            return httpx.Response(
                200,
                json=load_fixture("amadeus_flight_offers.json"),
                request=request,
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    provider = AmadeusFlightProvider(
        api_key="key-123",
        api_secret="secret-456",
        transport=httpx.MockTransport(handler),
        now_provider=lambda: now,
    )

    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=build_destination(),
            weekend_window=build_weekend_window(),
        )
    )

    assert len(requests) == 2
    token_request, search_request = requests
    assert token_request.method == "POST"
    assert token_request.url.path == "/v1/security/oauth2/token"
    token_body = token_request.content.decode()
    assert "grant_type=client_credentials" in token_body
    assert "client_id=key-123" in token_body
    assert "client_secret=secret-456" in token_body

    assert search_request.method == "GET"
    assert search_request.url.path == "/v2/shopping/flight-offers"
    assert search_request.headers["Authorization"] == "Bearer token-123"
    assert search_request.url.params["originLocationCode"] == "RIX"
    assert search_request.url.params["destinationLocationCode"] == "BGY"
    assert search_request.url.params["departureDate"] == "2026-07-10"
    assert search_request.url.params["returnDate"] == "2026-07-12"
    assert search_request.url.params["adults"] == "1"

    assert len(offers) == 2
    assert all(isinstance(offer, FlightOffer) for offer in offers)
    assert offers[0].provider == "amadeus"
    assert offers[0].origin == "RIX"
    assert offers[0].destination == "BGY"
    assert offers[0].price_eur == 75
    assert offers[0].airline == "BT"
    assert offers[0].stops == 0
    assert offers[0].booking_url is None
    assert offers[0].checked_at == now
    assert offers[1].stops == 1


def test_amadeus_provider_retries_once_on_transient_server_error() -> None:
    search_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal search_calls
        if request.url.path == "/v1/security/oauth2/token":
            return httpx.Response(
                200,
                json={"access_token": "token-123", "expires_in": 1800},
                request=request,
            )
        if request.url.path == "/v2/shopping/flight-offers":
            search_calls += 1
            if search_calls == 1:
                return httpx.Response(503, text="temporary error", request=request)
            return httpx.Response(
                200,
                json=load_fixture("amadeus_flight_offers.json"),
                request=request,
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    provider = AmadeusFlightProvider(
        api_key="key-123",
        api_secret="secret-456",
        transport=httpx.MockTransport(handler),
        now_provider=lambda: datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )

    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=build_destination(),
            weekend_window=build_weekend_window(),
        )
    )

    assert search_calls == 2
    assert offers


def test_amadeus_provider_does_not_retry_on_client_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.path == "/v1/security/oauth2/token":
            return httpx.Response(401, text="bad credentials", request=request)
        raise AssertionError(f"Unexpected path: {request.url.path}")

    provider = AmadeusFlightProvider(
        api_key="bad-key",
        api_secret="bad-secret",
        transport=httpx.MockTransport(handler),
        now_provider=lambda: datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(ProviderError) as exc_info:
        asyncio.run(
            provider.search_weekend_flights(
                origin="RIX",
                destination=build_destination(),
                weekend_window=build_weekend_window(),
            )
        )

    assert calls == 1
    assert "HTTP 401" in str(exc_info.value)

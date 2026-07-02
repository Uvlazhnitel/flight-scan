import asyncio
from datetime import date, time

from weekend_radar.models import Destination, FlightOffer, WeekendWindow
from weekend_radar.providers.base import FlightProvider
from weekend_radar.providers.mock import MockFlightProvider


def build_destination() -> Destination:
    return Destination(
        code="FCO",
        city="Rome",
        country="Italy",
        nature_score=3,
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


def test_mock_provider_implements_provider_interface() -> None:
    provider: FlightProvider = MockFlightProvider()

    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=build_destination(),
            weekend_window=build_weekend_window(),
        )
    )

    assert offers


def test_mock_provider_returns_valid_flight_offer_objects() -> None:
    provider = MockFlightProvider()

    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=build_destination(),
            weekend_window=build_weekend_window(),
        )
    )

    assert all(isinstance(offer, FlightOffer) for offer in offers)
    assert all(offer.origin == "RIX" for offer in offers)
    assert all(offer.destination == "FCO" for offer in offers)


def test_mock_provider_returns_expected_offer_mix() -> None:
    provider = MockFlightProvider()

    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=build_destination(),
            weekend_window=build_weekend_window(),
        )
    )

    assert len(offers) >= 6
    assert any(offer.price_eur < 60 and offer.stops == 0 for offer in offers)
    assert any(offer.price_eur >= 180 and offer.stops == 0 for offer in offers)
    assert any(offer.stops == 1 for offer in offers)
    assert any(offer.depart_at.time() < time(15, 0) for offer in offers)
    assert any(offer.return_depart_at.time() > time(23, 0) for offer in offers)


def test_mock_provider_returns_duplicate_like_offers() -> None:
    provider = MockFlightProvider()

    offers = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=build_destination(),
            weekend_window=build_weekend_window(),
        )
    )

    duplicate_like_offers = [
        offer
        for offer in offers
        if offer.depart_at.time() == time(17, 40)
        and offer.return_depart_at.time() == time(18, 20)
        and offer.price_eur == offers[4].price_eur
    ]

    assert len(duplicate_like_offers) >= 2
    assert duplicate_like_offers[0].booking_url != duplicate_like_offers[1].booking_url
    assert duplicate_like_offers[0].airline != duplicate_like_offers[1].airline


def test_mock_provider_is_deterministic_for_same_inputs() -> None:
    provider = MockFlightProvider()
    destination = build_destination()
    weekend_window = build_weekend_window()

    first = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=destination,
            weekend_window=weekend_window,
        )
    )
    second = asyncio.run(
        provider.search_weekend_flights(
            origin="RIX",
            destination=destination,
            weekend_window=weekend_window,
        )
    )

    assert first == second

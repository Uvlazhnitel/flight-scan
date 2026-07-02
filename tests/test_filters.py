from datetime import UTC, date, datetime, time

from weekend_radar.filters import (
    enabled_destinations,
    filter_useful_weekend_offers,
    is_useful_weekend_offer,
    weekend_flights,
)
from weekend_radar.models import (
    Destination,
    FlightOffer,
    OfferFilterRules,
    WeekendSearchRules,
    WeekendWindow,
)


def build_destination(*, enabled: bool = True) -> Destination:
    return Destination(
        code="FCO",
        city="Rome",
        country="Italy",
        nature_score=3,
        enabled=enabled,
    )


def build_weekend_window(pattern_name: str = "friday_evening_to_sunday_evening") -> WeekendWindow:
    is_monday_morning_pattern = pattern_name == "friday_evening_to_monday_morning"
    return WeekendWindow(
        depart_date=date(2026, 7, 10),
        return_date=date(2026, 7, 13) if is_monday_morning_pattern else date(2026, 7, 12),
        pattern_name=pattern_name,
        preferred_outbound_start_time=time(15, 0),
        preferred_outbound_end_time=time(22, 30),
        preferred_return_start_time=time(6, 0) if is_monday_morning_pattern else time(15, 0),
        preferred_return_end_time=time(11, 0) if is_monday_morning_pattern else time(23, 0),
        nights=3 if is_monday_morning_pattern else 2,
    )


def build_offer(
    *,
    price_eur: int = 99,
    stops: int = 0,
    depart_at: datetime | None = None,
    arrive_at: datetime | None = None,
    return_depart_at: datetime | None = None,
    return_arrive_at: datetime | None = None,
) -> FlightOffer:
    return FlightOffer(
        provider="mock",
        origin="RIX",
        destination="FCO",
        depart_at=depart_at or datetime(2026, 7, 10, 18, 0, tzinfo=UTC),
        arrive_at=arrive_at or datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
        return_depart_at=return_depart_at or datetime(2026, 7, 12, 20, 0, tzinfo=UTC),
        return_arrive_at=return_arrive_at or datetime(2026, 7, 12, 23, 0, tzinfo=UTC),
        price_eur=price_eur,
        stops=stops,
        checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )


def test_enabled_destinations_keeps_only_enabled_rows() -> None:
    destinations = [
        build_destination(enabled=True),
        Destination(
            code="BCN",
            city="Barcelona",
            country="Spain",
            nature_score=4,
            enabled=False,
        ),
    ]

    result = enabled_destinations(destinations)

    assert [item.code for item in result] == ["FCO"]


def test_weekend_flights_keeps_only_weekend_shape() -> None:
    weekend_rules = WeekendSearchRules()
    flights = [
        build_offer(),
        build_offer(
            depart_at=datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 8, 21, 0, tzinfo=UTC),
            return_depart_at=datetime(2026, 7, 9, 20, 0, tzinfo=UTC),
            return_arrive_at=datetime(2026, 7, 9, 23, 0, tzinfo=UTC),
        ),
    ]

    result = weekend_flights(flights, weekend_rules)

    assert len(result) == 1


def test_good_direct_cheap_weekend_deal_is_kept() -> None:
    result = is_useful_weekend_offer(
        build_offer(price_eur=99, stops=0),
        build_destination(),
        build_weekend_window(),
        OfferFilterRules(),
    )

    assert result


def test_too_expensive_offer_is_rejected() -> None:
    result = is_useful_weekend_offer(
        build_offer(price_eur=150),
        build_destination(),
        build_weekend_window(),
        OfferFilterRules(),
    )

    assert not result


def test_one_stop_rejected_when_direct_only_is_true() -> None:
    result = is_useful_weekend_offer(
        build_offer(stops=1),
        build_destination(),
        build_weekend_window(),
        OfferFilterRules(direct_only=True),
    )

    assert not result


def test_late_arrival_rejected() -> None:
    result = is_useful_weekend_offer(
        build_offer(arrive_at=datetime(2026, 7, 11, 0, 45, tzinfo=UTC)),
        build_destination(),
        build_weekend_window(),
        OfferFilterRules(),
    )

    assert not result


def test_very_early_departure_rejected() -> None:
    result = is_useful_weekend_offer(
        build_offer(depart_at=datetime(2026, 7, 10, 5, 45, tzinfo=UTC)),
        build_destination(),
        build_weekend_window(),
        OfferFilterRules(),
    )

    assert not result


def test_disabled_destination_rejected() -> None:
    result = is_useful_weekend_offer(
        build_offer(),
        build_destination(enabled=False),
        build_weekend_window(),
        OfferFilterRules(),
    )

    assert not result


def test_monday_morning_return_before_six_is_allowed() -> None:
    monday_window = build_weekend_window("friday_evening_to_monday_morning")
    offer = build_offer(
        return_depart_at=datetime(2026, 7, 13, 5, 30, tzinfo=UTC),
        return_arrive_at=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
    )

    result = is_useful_weekend_offer(
        offer,
        build_destination(),
        monday_window,
        OfferFilterRules(),
    )

    assert result


def test_filter_useful_weekend_offers_returns_only_useful_items() -> None:
    offers = [
        build_offer(price_eur=99),
        build_offer(price_eur=170),
        build_offer(stops=1),
    ]

    result = filter_useful_weekend_offers(
        offers,
        build_destination(),
        build_weekend_window(),
        OfferFilterRules(),
    )

    assert [offer.price_eur for offer in result] == [99]

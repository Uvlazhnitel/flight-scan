from datetime import UTC, date, datetime, time

from weekend_radar.models import Destination, FlightOffer, WeekendWindow
from weekend_radar.scoring import build_deal_candidate, score_offer
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


def build_destination(*, nature_score: int = 3) -> Destination:
    return Destination(
        code="FCO",
        city="Rome",
        country="Italy",
        nature_score=nature_score,
    )


def build_offer(
    *,
    price_eur: int = 49,
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
        arrive_at=arrive_at or datetime(2026, 7, 10, 20, 30, tzinfo=UTC),
        return_depart_at=return_depart_at or datetime(2026, 7, 12, 18, 0, tzinfo=UTC),
        return_arrive_at=return_arrive_at or datetime(2026, 7, 12, 20, 30, tzinfo=UTC),
        price_eur=price_eur,
        stops=stops,
        checked_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )


def test_excellent_deal_scores_high_with_clear_reasons() -> None:
    score = score_offer(
        build_offer(price_eur=49),
        build_destination(nature_score=8),
        build_weekend_window(),
    )

    assert score.total_score == 92
    assert score.reasons == [
        "Exceptional price at or below 50 EUR",
        "Direct flight keeps the trip simple",
        "Outbound timing fits the preferred weekend window",
        "Return timing fits the preferred weekend window",
        "Destination nature appeal adds 12 points",
    ]
    assert score.warnings == []


def test_cheap_but_terrible_timing_collects_warnings() -> None:
    score = score_offer(
        build_offer(
            price_eur=49,
            depart_at=datetime(2026, 7, 10, 5, 15, tzinfo=UTC),
            arrive_at=datetime(2026, 7, 11, 0, 45, tzinfo=UTC),
        ),
        build_destination(),
        build_weekend_window(),
    )

    assert score.total_score == 34
    assert "Exceptional price at or below 50 EUR" in score.reasons
    assert "Outbound timing fits the preferred weekend window" not in score.reasons
    assert score.warnings == [
        "Late outbound arrival after 00:30",
        "Outbound departure is before 06:00",
    ]


def test_expensive_but_good_timing_stays_rankable() -> None:
    score = score_offer(
        build_offer(price_eur=150),
        build_destination(nature_score=4),
        build_weekend_window(),
    )

    assert score.total_score == 56
    assert score.reasons == [
        "Direct flight keeps the trip simple",
        "Outbound timing fits the preferred weekend window",
        "Return timing fits the preferred weekend window",
        "Destination nature appeal adds 6 points",
    ]
    assert score.warnings == []


def test_nature_destination_boost_scales_to_fifteen_points() -> None:
    score = score_offer(
        build_offer(price_eur=80),
        build_destination(nature_score=10),
        build_weekend_window(),
    )

    assert "Destination nature appeal adds 15 points" in score.reasons


def test_direct_vs_one_stop_changes_score_and_warnings() -> None:
    direct_score = score_offer(
        build_offer(price_eur=80, stops=0),
        build_destination(),
        build_weekend_window(),
    )
    one_stop_score = score_offer(
        build_offer(price_eur=80, stops=1),
        build_destination(),
        build_weekend_window(),
    )

    assert direct_score.total_score == 74
    assert one_stop_score.total_score == 39
    assert "Direct flight keeps the trip simple" in direct_score.reasons
    assert one_stop_score.warnings == ["One-stop itinerary adds travel friction"]


def test_score_stability_for_same_input() -> None:
    flight = build_offer(price_eur=80, stops=1)
    destination = build_destination(nature_score=7)
    weekend_window = build_weekend_window()

    first = score_offer(flight, destination, weekend_window)
    second = score_offer(flight, destination, weekend_window)

    assert first == second


def test_deal_message_can_use_score_reasons() -> None:
    notifier = TelegramNotifier(chat_id="demo")
    candidate = build_deal_candidate(
        build_offer(price_eur=49),
        build_destination(nature_score=8),
        build_weekend_window(),
    )

    message = notifier.format_deal_candidate(candidate)

    assert "Score: 92" in message
    assert "Exceptional price at or below 50 EUR" in message

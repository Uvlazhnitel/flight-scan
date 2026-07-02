"""Date helpers for deterministic weekend search-window generation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from weekend_radar.models import WeekendSearchRules, WeekendWindow

RIGA_TIMEZONE = ZoneInfo("Europe/Riga")
FRIDAY_EVENING_START = time(hour=15, minute=0)
FRIDAY_EVENING_END = time(hour=22, minute=30)
SATURDAY_MORNING_START = time(hour=6, minute=0)
SATURDAY_MORNING_END = time(hour=11, minute=30)
SUNDAY_EVENING_START = time(hour=15, minute=0)
SUNDAY_EVENING_END = time(hour=23, minute=0)
MONDAY_MORNING_START = time(hour=6, minute=0)
MONDAY_MORNING_END = time(hour=11, minute=0)

WEEKEND_PATTERNS: tuple[dict[str, object], ...] = (
    {
        "pattern_name": "friday_evening_to_sunday_evening",
        "depart_offset_days": 0,
        "return_offset_days": 2,
        "preferred_outbound_start_time": FRIDAY_EVENING_START,
        "preferred_outbound_end_time": FRIDAY_EVENING_END,
        "preferred_return_start_time": SUNDAY_EVENING_START,
        "preferred_return_end_time": SUNDAY_EVENING_END,
        "nights": 2,
    },
    {
        "pattern_name": "friday_evening_to_monday_morning",
        "depart_offset_days": 0,
        "return_offset_days": 3,
        "preferred_outbound_start_time": FRIDAY_EVENING_START,
        "preferred_outbound_end_time": FRIDAY_EVENING_END,
        "preferred_return_start_time": MONDAY_MORNING_START,
        "preferred_return_end_time": MONDAY_MORNING_END,
        "nights": 3,
    },
    {
        "pattern_name": "saturday_morning_to_sunday_evening",
        "depart_offset_days": 1,
        "return_offset_days": 2,
        "preferred_outbound_start_time": SATURDAY_MORNING_START,
        "preferred_outbound_end_time": SATURDAY_MORNING_END,
        "preferred_return_start_time": SUNDAY_EVENING_START,
        "preferred_return_end_time": SUNDAY_EVENING_END,
        "nights": 1,
    },
    {
        "pattern_name": "saturday_morning_to_monday_morning",
        "depart_offset_days": 1,
        "return_offset_days": 3,
        "preferred_outbound_start_time": SATURDAY_MORNING_START,
        "preferred_outbound_end_time": SATURDAY_MORNING_END,
        "preferred_return_start_time": MONDAY_MORNING_START,
        "preferred_return_end_time": MONDAY_MORNING_END,
        "nights": 2,
    },
)


def is_weekend_date(value: date) -> bool:
    """Return True for Saturday and Sunday."""

    return value.weekday() >= 5


def is_weekend_trip(depart_date: date, return_date: date) -> bool:
    """Return True when a trip starts on Friday/Saturday and returns on Sunday/Monday."""

    departure_ok = depart_date.weekday() in {4, 5}
    return_ok = return_date.weekday() in {6, 0}
    return departure_ok and return_ok and return_date >= depart_date


def next_weekend_start(from_date: date) -> date:
    """Return the next Saturday on or after the provided date."""

    offset = (5 - from_date.weekday()) % 7
    return from_date + timedelta(days=offset)


def _as_riga_datetime(current_at: datetime | None) -> datetime:
    """Normalize the injected current time to a Riga-local timezone-aware datetime."""

    if current_at is None:
        return datetime.now(RIGA_TIMEZONE)
    if current_at.tzinfo is None or current_at.utcoffset() is None:
        raise ValueError("current_at must be timezone-aware")
    return current_at.astimezone(RIGA_TIMEZONE)


def _friday_anchor_for(date_value: date) -> date:
    """Return the Friday date for the next weekend group on or after the provided date."""

    return date_value + timedelta(days=(4 - date_value.weekday()) % 7)


def _build_window(friday_anchor: date, pattern: dict[str, object]) -> WeekendWindow:
    """Create one concrete weekend window from a Friday anchor and pattern definition."""

    depart_date = friday_anchor + timedelta(days=int(pattern["depart_offset_days"]))
    return_date = friday_anchor + timedelta(days=int(pattern["return_offset_days"]))
    return WeekendWindow(
        depart_date=depart_date,
        return_date=return_date,
        pattern_name=str(pattern["pattern_name"]),
        preferred_outbound_start_time=pattern["preferred_outbound_start_time"],
        preferred_outbound_end_time=pattern["preferred_outbound_end_time"],
        preferred_return_start_time=pattern["preferred_return_start_time"],
        preferred_return_end_time=pattern["preferred_return_end_time"],
        nights=int(pattern["nights"]),
    )


def _window_is_still_available(window: WeekendWindow, current_at: datetime) -> bool:
    """Exclude windows whose outbound preferred time range has already fully passed."""

    outbound_end = datetime.combine(
        window.depart_date,
        window.preferred_outbound_end_time,
        tzinfo=RIGA_TIMEZONE,
    )
    return current_at <= outbound_end


def generate_weekend_windows(
    current_at: datetime | None = None,
    rules: WeekendSearchRules | None = None,
) -> list[WeekendWindow]:
    """Generate the next configured Riga weekend windows in chronological order."""

    active_rules = rules or WeekendSearchRules()
    riga_now = _as_riga_datetime(current_at)
    friday_anchor = _friday_anchor_for(riga_now.date())
    allowed_patterns = {
        str(pattern["pattern_name"]): pattern
        for pattern in WEEKEND_PATTERNS
        if str(pattern["pattern_name"]) in active_rules.enabled_patterns
    }

    windows: list[WeekendWindow] = []
    week_offset = 0
    while len(windows) < active_rules.future_windows_count:
        current_friday = friday_anchor + timedelta(days=7 * week_offset)
        week_candidates = [
            _build_window(current_friday, pattern) for pattern in allowed_patterns.values()
        ]
        week_candidates.sort(
            key=lambda window: (
                window.depart_date,
                window.preferred_outbound_start_time,
                window.return_date,
                window.preferred_return_start_time,
            )
        )
        for candidate in week_candidates:
            if _window_is_still_available(candidate, riga_now):
                windows.append(candidate)
                if len(windows) >= active_rules.future_windows_count:
                    break
        week_offset += 1

    return windows

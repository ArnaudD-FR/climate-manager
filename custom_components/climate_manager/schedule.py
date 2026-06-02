# SPDX-License-Identifier: MIT
"""Climate Manager schedule and presence evaluation engine.

Pure Python — no Home Assistant imports.
All functions accept datetime objects directly; callers supply dt_util.now().

Requirements addressed:
- SCHED-01: global time program per-day periods with time entries
- SCHED-02: each period active from start until next period's start
- SCHED-03: last period of day ends at midnight (next day takes over)
- SCHED-04: per-day schema (D-01) — each day has its own period list
- PERSON-01: presence modes (automatic, present, absent)
- PERSON-02: present mode → always True
- PERSON-03: absent mode → always False
- PERSON-04: automatic mode → evaluate person's periodic schedule
- PERSON-05: automatic + no schedule → False (absent by default)
- PERSON-07: present person → heat from first Normal/Comfort period to end of last
- PERSON-08: sandwiched Reduced/Frost between two N/C periods → hold preceding N/C temp
- PERSON-09: absent person → Reduced temperature
- GLOBAL-03: configurable period mode temperatures (caller provides period_temperatures)
- D-01: per-day schema {"mon": [...], ..., "sun": [...]} for all programs
- D-05: present + no N/C periods today → Reduced temperature
"""

import datetime
import logging
import re

from .const import (
    GAP_HANDLING_DAY_SPAN,
    GAP_HANDLING_THRESHOLD,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    PRESENCE_ABSENT,
    PRESENCE_AUTOMATIC,
    PRESENCE_CALENDAR,
    PRESENCE_HA,
    PRESENCE_PRESENT,
)

# ---------------------------------------------------------------------------
# Day name → Python weekday() mapping (0=Mon ... 6=Sun)
# ---------------------------------------------------------------------------

DAY_TO_WEEKDAY: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

# Reverse mapping for per-day schema: weekday() int → day name string (D-01)
WEEKDAY_TO_DAY: dict[int, str] = {v: k for k, v in DAY_TO_WEEKDAY.items()}

ALL_DAYS: set[str] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

# Matches zero-padded HH:MM time strings (e.g. "09:30", "22:00").
# Non-zero-padded strings like "9:30" are intentionally rejected so that
# the sort-by-parsed-time guarantee (CR-01) is enforced at input time.
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_time(value: str) -> datetime.time:
    """Parse an "HH:MM" string into a datetime.time object.

    Called by all evaluation functions for period start time comparison.
    """
    h, m = map(int, value.split(":"))
    return datetime.time(h, m)


def _local_day_fallback(d: datetime.date) -> datetime.datetime:
    """Fallback for start_of_local_day when no callable is provided.

    Returns a UTC-midnight aware datetime for the given date.
    This fallback is only used in pure unit tests where dt_util is
    unavailable. Production callers MUST pass dt_util.start_of_local_day.
    """
    return datetime.datetime(
        d.year, d.month, d.day, tzinfo=datetime.timezone.utc
    )


def _parse_calendar_dt(
    s: str,
    start_of_local_day,
) -> datetime.datetime:
    """Parse an ISO calendar event start/end string to an aware datetime.

    Handles two formats from HA calendar.get_events:
    - Timed event: "2026-06-01T08:00:00+02:00" → datetime with offset
    - All-day event: "2026-06-01" → local-midnight aware datetime via
      start_of_local_day callable (Landmine 3: never compare naive vs aware)

    Args:
        s: ISO date or datetime string from the event dict.
        start_of_local_day: Callable(date) → aware datetime. Production
            callers pass dt_util.start_of_local_day. Tests may pass
            the same or the _local_day_fallback.

    Raises:
        ValueError: if the string cannot be parsed as a valid date or
            datetime — callers should catch and skip the offending event.
    """
    try:
        if "T" in s:
            return datetime.datetime.fromisoformat(s)
        d = datetime.date.fromisoformat(s)
        return start_of_local_day(d)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Unparseable calendar datetime {s!r}") from exc


def _parse_events(
    events: list[dict],
    sol,
) -> list[tuple[datetime.datetime, datetime.datetime]]:
    """Parse and sort calendar event dicts into (start, end) tuples.

    Skips malformed or unparseable entries with a warning log.
    Returns events sorted ascending by start time.
    """
    parsed: list[tuple[datetime.datetime, datetime.datetime]] = []
    for event in events:
        start_s = event.get("start", "")
        end_s = event.get("end", "")
        if not start_s or not end_s:
            continue
        try:
            parsed.append(
                (
                    _parse_calendar_dt(start_s, sol),
                    _parse_calendar_dt(end_s, sol),
                )
            )
        except ValueError:
            _LOGGER.warning(
                "Skipping calendar event with unparseable datetime: %r", event
            )
    parsed.sort(key=lambda e: e[0])
    return parsed


def _is_calendar_active(
    events: list[dict],
    now: datetime.datetime,
    gap_handling: str,
    gap_threshold_minutes: int,
    sol,
) -> bool:
    """Return True if *now* falls inside a 'calendar-active' window.

    gap_handling controls how gaps between events are treated:
    - "exact" (default): gaps are not active — person returns home.
    - "day_span": entire span from first event start to last event end
      is active — gaps are absorbed.
    - "threshold": gaps shorter than gap_threshold_minutes are active
      (person stays away); longer gaps trigger a return home.
    """
    parsed = _parse_events(events, sol)
    if not parsed:
        return False

    if gap_handling == GAP_HANDLING_DAY_SPAN:
        return parsed[0][0] <= now < parsed[-1][1]

    if gap_handling == GAP_HANDLING_THRESHOLD:
        for start, end in parsed:
            if start <= now < end:
                return True
        td = datetime.timedelta(minutes=gap_threshold_minutes)
        for i in range(len(parsed) - 1):
            gap_start, gap_end = parsed[i][1], parsed[i + 1][0]
            if gap_start <= now < gap_end:
                return (gap_end - gap_start) <= td
        return False

    # "exact" (default)
    return any(start <= now < end for start, end in parsed)


def resolve_calendar_presence(
    events: list[dict],
    event_means: str,
    now: datetime.datetime,
    gap_handling: str = "exact",
    gap_threshold_minutes: int = 0,
    preheat_lead_minutes: int = 60,
    start_of_local_day=None,
) -> bool:
    """Return True if the person should be considered present.

    CAL-01, CAL-04, D-10.

    Args:
        events: List of event dicts from _calendar_cache[entity_id].
        event_means: "absent" | "present" — what an active calendar
            period means.
        now: Current timezone-aware datetime (from dt_util.now()).
        gap_handling: "exact" | "day_span" | "threshold" — controls
            how gaps between calendar events are treated.
        gap_threshold_minutes: Only used when gap_handling="threshold".
            Gaps shorter than this are treated as active (person stays
            away); longer gaps trigger a return home.
        preheat_lead_minutes: Reserved for future morning pre-heat (D-10).
            Currently unused.
        start_of_local_day: Callable(date) → aware datetime. Tests may
            omit this; production callers MUST pass dt_util.start_of_local_day.
    """
    _sol = (
        start_of_local_day
        if start_of_local_day is not None
        else _local_day_fallback
    )
    active = _is_calendar_active(
        events, now, gap_handling, gap_threshold_minutes, _sol
    )
    if event_means == "absent":
        return not active
    return active


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_schedule(
    daily_program: dict[str, list],
    now: datetime.datetime,
) -> str:
    """Return the active period_mode for the current time.

    Algorithm:
    1. Look up today's period list directly from the per-day dict using the
       day name resolved from now.weekday() via WEEKDAY_TO_DAY.
    2. Sort periods by start time ascending.
    3. Walk periods in order, keeping the last period whose start <= now.time()
       (>= comparison: exact boundary minute belongs to the new period — Pitfall 4).
    4. Return the active period's mode. If no period has started yet or the day
       key is absent, return PERIOD_FROST_PROTECTION.

    SCHED-02: each period active from start until next period's start.
    SCHED-03: last period of day ends at midnight; next day takes over.
    T-03-01: daily_program.get(day_name, []) returns [] for missing keys →
             falls back to PERIOD_FROST_PROTECTION instead of raising KeyError.
    """
    day_name = WEEKDAY_TO_DAY[now.weekday()]  # e.g. "mon"
    current_time = now.time()

    periods = daily_program.get(day_name, [])
    if not periods:
        return PERIOD_FROST_PROTECTION

    sorted_periods = sorted(periods, key=lambda p: _parse_time(p["start"]))
    active_mode = None
    for period in sorted_periods:
        period_start = _parse_time(period["start"])
        if current_time >= period_start:
            active_mode = period["mode"]
        else:
            break
    return active_mode if active_mode is not None else PERIOD_FROST_PROTECTION


def resolve_presence(
    person_config: dict,
    now: datetime.datetime,
    calendar_cache: dict | None = None,
    start_of_local_day=None,
) -> bool:
    """Return True if the person is currently present.

    PERSON-02: Present mode → always True.
    PERSON-03: Absent mode → always False.
    PERSON-04: Automatic → evaluate person's periodic schedule.
    PERSON-05: Automatic + no schedule configured → False (absent by default).

    Missing 'mode' key defaults to PRESENCE_AUTOMATIC.
    The 'schedule' value is a per-day dict (D-01): {"mon": [...], ..., "sun": [...]}.

    Args:
        person_config: Person configuration dict.
        now: Current timezone-aware datetime.
        calendar_cache: Optional pre-fetched calendar event cache keyed by
            entity_id (D-13). Required when any period has state="calendar".
            If None or missing key, falls back to empty events list.
            Production callers (coordinator.py) populate this before calling.
        start_of_local_day: Callable(date) → aware datetime for all-day
            event parsing (Landmine 3). Passed through to
            resolve_calendar_presence(). Defaults to _local_day_fallback.
    """
    mode = person_config.get("mode", PRESENCE_AUTOMATIC)

    if mode == PRESENCE_PRESENT:
        return True
    if mode == PRESENCE_ABSENT:
        return False

    # Automatic: evaluate periodic schedule (per-day dict, D-01)
    # SCHED-02: select the correct week schedule based on ISO week parity
    schedule_type = person_config.get("schedule_type", "single")
    if schedule_type == "even_odd":
        # Known limitation (WR-03): ISO week parity is derived from the raw
        # ISO week number modulo 2. In years that contain an ISO week 53
        # (e.g. 2026, 2032), week 53 is odd and the immediately following
        # week 1 of the next year is also odd — resulting in two consecutive
        # "odd" weeks at the year boundary and one skipped "even" week.
        # This is an accepted limitation for v1. A future version may anchor
        # parity to a fixed reference date to guarantee strict alternation
        # across all year boundaries.
        week_parity = now.date().isocalendar().week % 2
        schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
        schedule = person_config.get(schedule_key, {})
    else:
        schedule = person_config.get("schedule", {})
    day_name = WEEKDAY_TO_DAY[now.weekday()]
    periods = schedule.get(day_name, [])
    if not periods:
        return False  # PERSON-05: no periods today → absent

    current_time = now.time()

    # Walk sorted periods to find active presence state
    sorted_periods = sorted(periods, key=lambda p: _parse_time(p["start"]))
    active_period = None
    active_state = "absent"  # default before first period
    for period in sorted_periods:
        period_start = _parse_time(period["start"])
        if current_time >= period_start:
            active_state = period["state"]
            active_period = period
        else:
            break

    # Handle period state "calendar" (D-06, CAL-03 — per-period calendar_config)
    # D-07: not recursive — calendar period inside calendar mode is not supported.
    if active_state == "calendar" and active_period is not None:
        cal_cfg = active_period.get("calendar_config") or {}
        entity_id = cal_cfg.get("entity_id", "")
        event_means = cal_cfg.get("event_means", "absent")
        events = (calendar_cache or {}).get(entity_id, [])
        preheat = person_config.get(
            "wakeup_advance_minutes",
            person_config.get("preheat_lead_minutes", 60),
        )
        return resolve_calendar_presence(
            events,
            event_means,
            now,
            gap_handling=cal_cfg.get("gap_handling", "exact"),
            gap_threshold_minutes=cal_cfg.get("gap_threshold_minutes", 0),
            preheat_lead_minutes=preheat,
            start_of_local_day=start_of_local_day,
        )

    # Note: period schedule states are binary literals "present"/"absent"
    # (PERSON-04), NOT the presence mode constants PRESENCE_PRESENT/
    # PRESENCE_ABSENT (D-21).
    return active_state == "present"


def next_occupied_at(
    person_config: dict,
    now: datetime.datetime,
    calendar_cache: dict | None = None,
    start_of_local_day=None,
) -> datetime.datetime | None:
    """Return the next datetime when the person transitions to present.

    D-03 / PREHEAT-05: supplies the next-transition value the pre-heat
    trigger condition depends on (now >= next_occupied_at - learned_lead).

    Mode dispatch:
    - PRESENCE_HA, PRESENCE_PRESENT (force_present),
      PRESENCE_ABSENT (force_absent) → None
    - PRESENCE_CALENDAR → end of active absent-event OR start of next
      present-event (from calendar_cache)
    - Automatic (scheduled) single/even_odd → start of the first present
      period strictly after `now` within a 7-day lookahead

    Returned datetimes are always timezone-aware with the same tzinfo
    as `now`.  Never mixes naive/aware (Pitfall 2).

    Args:
        person_config: Person configuration dict.
        now: Current timezone-aware datetime.
        calendar_cache: Optional pre-fetched calendar events keyed by
            entity_id.  Required for PRESENCE_CALENDAR mode.
        start_of_local_day: Callable(date) → aware datetime.  Only used
            for all-day calendar event parsing.  Defaults to
            _local_day_fallback.
    """
    mode = person_config.get("mode", PRESENCE_AUTOMATIC)

    # Modes with no predictable next-occupied transition
    if mode in (PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT):
        return None

    if mode == PRESENCE_CALENDAR:
        return _next_occupied_calendar(
            person_config, now, calendar_cache, start_of_local_day
        )

    # Automatic (scheduled) — single or even_odd
    return _next_occupied_scheduled(person_config, now)


def _next_occupied_calendar(
    person_config: dict,
    now: datetime.datetime,
    calendar_cache: dict | None,
    start_of_local_day,
) -> datetime.datetime | None:
    """Return next-occupied datetime for calendar-mode persons.

    event_means="absent": person returns home when the active event ends
        → return that event's end datetime.
    event_means="present": person is next home at the start of the next
        event after now → return that event's start datetime.
    """
    _sol = (
        start_of_local_day
        if start_of_local_day is not None
        else _local_day_fallback
    )
    cal_cfg = person_config.get("calendar_config") or {}
    entity_id = cal_cfg.get("entity_id", "")
    event_means = cal_cfg.get("event_means", "absent")
    raw_events = (calendar_cache or {}).get(entity_id, [])
    events = _parse_events(raw_events, _sol)

    if event_means == "absent":
        # Person is absent during events.  If we are inside an event,
        # the next transition to present is the event's end time.
        for start, end in events:
            if start <= now < end and end > now:
                return end
        return None

    # event_means == "present": person is present during events.
    # Return the start of the first event that begins strictly after now.
    for start, end in events:
        if start > now:
            return start
    return None


def _next_occupied_scheduled(
    person_config: dict,
    now: datetime.datetime,
) -> datetime.datetime | None:
    """Return next-occupied datetime for automatic (scheduled) persons.

    Walks a 7-day lookahead from now.  For each target date selects the
    correct schedule (single vs even_odd) using that day's ISO week parity.
    Returns the start of the first present period strictly after now.
    """
    schedule_type = person_config.get("schedule_type", "single")

    for day_offset in range(7):
        target_date = now.date() + datetime.timedelta(days=day_offset)

        if schedule_type == "even_odd":
            week_parity = target_date.isocalendar().week % 2
            schedule_key = (
                "schedule_even" if week_parity == 0 else "schedule_odd"
            )
            schedule = person_config.get(schedule_key, {})
        else:
            schedule = person_config.get("schedule", {})

        day_name = WEEKDAY_TO_DAY[target_date.weekday()]
        periods = schedule.get(day_name, [])
        if not periods:
            continue

        sorted_periods = sorted(periods, key=lambda p: _parse_time(p["start"]))
        for period in sorted_periods:
            if period.get("state") != "present":
                continue
            # Build the candidate aware datetime for this period start
            candidate = datetime.datetime.combine(
                target_date,
                _parse_time(period["start"]),
            ).replace(tzinfo=now.tzinfo)
            if candidate > now:
                return candidate

    return None


def compute_occupied_temp(
    daily_program: dict[str, list],
    now: datetime.datetime,
    is_present: bool,
    period_temperatures: dict[str, float],
) -> tuple[float, str]:
    """Return (desired_temperature, effective_period_name) for a person-associated room.

    PERSON-07: present → heat continuously from first Normal/Comfort period
               to end of last Normal/Comfort period of the day.
    PERSON-08: sandwiched Reduced/Frost period between two N/C periods
               → hold temperature of the preceding Normal/Comfort period (gap-fill).
    PERSON-09: absent → PERIOD_REDUCED temperature always.
    D-05: present + today has no Normal/Comfort periods → PERIOD_REDUCED temperature.

    Returns a (temperature, period_name) tuple so callers can surface the effective
    period in the status payload without re-deriving it from the temperature value.
    """
    if not is_present:
        return period_temperatures[PERIOD_REDUCED], PERIOD_REDUCED

    day_name = WEEKDAY_TO_DAY[now.weekday()]
    current_time = now.time()

    # Find today's periods from the per-day dict (D-01)
    today_periods = sorted(
        daily_program.get(day_name, []),
        key=lambda p: _parse_time(p["start"]),
    )

    # Identify Normal/Comfort periods
    nc_modes = {PERIOD_NORMAL, PERIOD_COMFORT}
    nc_periods = [p for p in today_periods if p["mode"] in nc_modes]

    if not nc_periods:
        # D-05: no Normal/Comfort periods at all → apply Reduced
        _LOGGER.debug(
            "compute_occupied_temp: no N/C periods for today (%s)"
            " — returning Reduced for present person",
            day_name,
        )
        return period_temperatures[PERIOD_REDUCED], PERIOD_REDUCED

    # Occupied window: [start of first N/C, start of period after last N/C]
    first_nc_start = _parse_time(nc_periods[0]["start"])

    # End of occupied window = start of the period immediately after the last N/C,
    # or None if the last N/C is the final period of the day (window extends to midnight).
    # Use identity-based search (not list.index()) so duplicate dicts do not
    # cause the wrong index to be returned (WR-02).
    last_nc_idx = next(
        i for i, p in enumerate(today_periods) if p is nc_periods[-1]
    )
    if last_nc_idx + 1 < len(today_periods):
        occupied_end: datetime.time | None = _parse_time(
            today_periods[last_nc_idx + 1]["start"]
        )
    else:
        occupied_end = (
            None  # last N/C is last period — window extends to midnight
        )

    # Before the occupied window → Reduced
    if current_time < first_nc_start:
        return period_temperatures[PERIOD_REDUCED], PERIOD_REDUCED

    # After the occupied window → Reduced
    if occupied_end is not None and current_time >= occupied_end:
        return period_temperatures[PERIOD_REDUCED], PERIOD_REDUCED

    # Within the occupied window: walk periods forward tracking last N/C mode seen
    active_mode = None
    last_nc_mode_seen = None
    for period in today_periods:
        pstart = _parse_time(period["start"])
        if pstart > current_time:
            break
        if period["mode"] in nc_modes:
            last_nc_mode_seen = period["mode"]
        active_mode = period["mode"]

    # PERSON-08 gap-fill: if active period is Reduced/Frost but we're inside the
    # occupied window, substitute the temperature of the preceding N/C period.
    if active_mode not in nc_modes and last_nc_mode_seen is not None:
        active_mode = last_nc_mode_seen

    effective = active_mode if active_mode is not None else PERIOD_REDUCED
    return period_temperatures.get(
        effective, period_temperatures[PERIOD_REDUCED]
    ), effective


def validate_daily_program(
    daily_program: dict[str, list],
) -> tuple[bool, str]:
    """Validate that the per-day dict contains exactly all 7 day keys.

    Returns (True, '') if valid, (False, error_message) if invalid.
    Called at config save time (Phase 3 WebSocket handler) and exercised by unit tests.

    D-01: programs must use the per-day schema with all 7 day keys (Mon–Sun).
    Unknown day keys are also rejected.

    Period-level validation (WR-01):
    - Each period must have a "start" key with a zero-padded "HH:MM" value.
    - Each period must have a "mode" or "state" key.
    - No two periods in the same day may share the same start time.
    """
    missing = ALL_DAYS - set(daily_program.keys())
    extra = set(daily_program.keys()) - ALL_DAYS

    parts = []
    if missing:
        parts.append(f"Missing days: {', '.join(sorted(missing))}")
    if extra:
        parts.append(f"Unknown days: {', '.join(sorted(extra))}")
    if parts:
        return False, "; ".join(parts)

    # Period-level validation for each day
    for day, periods in daily_program.items():
        if day not in ALL_DAYS:
            continue
        starts_seen: set[str] = set()
        for i, period in enumerate(periods):
            if "start" not in period:
                return False, f"{day}[{i}]: missing 'start' key"
            if not _TIME_RE.match(period["start"]):
                return False, (
                    f"{day}[{i}]: 'start' must be HH:MM (zero-padded),"
                    f" got {period['start']!r}"
                )
            if period["start"] in starts_seen:
                return (
                    False,
                    f"{day}[{i}]: duplicate start time {period['start']!r}",
                )
            starts_seen.add(period["start"])
            if "mode" not in period and "state" not in period:
                return (
                    False,
                    f"{day}[{i}]: period must have 'mode' or 'state'",
                )

    return True, ""

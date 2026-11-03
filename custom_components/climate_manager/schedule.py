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
    PRESENCE_PERIOD_ABSENT,
    PRESENCE_PERIOD_PRESENT,
    PRESENCE_PRESENT,
    VALID_ABSENCE_SETBACKS,
    VALID_PRESENCE_PERIOD_KINDS,
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

# Local date and time of a presence period bound, without time zone.
_LOCAL_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")

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


def _active_window_end(
    events: list[dict],
    now: datetime.datetime,
    gap_handling: str,
    gap_threshold_minutes: int,
    sol,
) -> datetime.datetime | None:
    """Return when the calendar-active window containing *now* ends.

    This is the moment the person would transition back to "not absent"
    (return home) under the given gap_handling, or None when *now* is not
    inside an active window. Callers only invoke this once *now* is known
    to be active, so a containing run is always found in that case.

    Used by CAL-04 (D-10): a calendar-absent person is treated as present
    once this end falls within the wake-up lead, so rooms pre-heat before
    the person returns.
    """
    parsed = _parse_events(events, sol)
    if not parsed:
        return None

    if gap_handling == GAP_HANDLING_DAY_SPAN:
        if parsed[0][0] <= now < parsed[-1][1]:
            return parsed[-1][1]
        return None

    # "exact" merges only touching/overlapping events (td=0); "threshold"
    # also absorbs gaps up to gap_threshold_minutes. Either way the active
    # window is the contiguous run of events (plus merged short gaps) that
    # contains *now*, and it ends when that run ends — matching the present↔
    # absent boundary _is_calendar_active draws for the same mode.
    td = (
        datetime.timedelta(minutes=gap_threshold_minutes)
        if gap_handling == GAP_HANDLING_THRESHOLD
        else datetime.timedelta(0)
    )
    run_start, run_end = parsed[0]
    for start, end in parsed[1:]:
        if start - run_end <= td:
            run_end = max(run_end, end)
        else:
            if run_start <= now < run_end:
                return run_end
            run_start, run_end = start, end
    if run_start <= now < run_end:
        return run_end
    return None


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
        preheat_lead_minutes: Wake-up advance (CAL-04, D-10). When
            event_means="absent" and an event is active, the person is
            treated as present once that active window ends within this
            many minutes, so rooms pre-heat before the person returns.
            0 disables the wake-up advance. No effect when
            event_means="present".
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
        if not active:
            return True
        # CAL-04: the active window means "away", but once it ends within
        # the wake-up lead, treat the person as present so the zone schedule
        # applies and rooms pre-heat ahead of their return.
        if preheat_lead_minutes and preheat_lead_minutes > 0:
            window_end = _active_window_end(
                events, now, gap_handling, gap_threshold_minutes, _sol
            )
            if (
                window_end is not None
                and window_end - now
                <= datetime.timedelta(minutes=preheat_lead_minutes)
            ):
                return True
        return False
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


def next_setpoint_increase_at(
    time_program: dict,
    period_temperatures: dict[str, float],
    now: datetime.datetime,
) -> datetime.datetime | None:
    """Return the next datetime when the zone time program transitions to a
    period with a strictly higher temperature than the period before it.

    Each transition is compared with the temperature in effect just before
    it, not with the current one: in Normal at 18:00, the next increase is
    tomorrow's Reduced -> Normal at 07:00, past tonight's drop to Reduced.

    Scans up to 7 days ahead. Returns None if no such transition exists in
    that window (e.g. a single period all week).

    Used by the pre-heat trigger so that pre-heat fires based on the zone
    schedule's own setpoint increases, not on person presence transitions.
    """
    current_period = evaluate_schedule(time_program, now)
    previous_temp = period_temperatures.get(current_period)
    if previous_temp is None:
        return None

    for day_offset in range(8):
        target_date = now.date() + datetime.timedelta(days=day_offset)
        day_name = WEEKDAY_TO_DAY[target_date.weekday()]
        periods = time_program.get(day_name, [])
        if not periods:
            continue

        sorted_periods = sorted(periods, key=lambda p: _parse_time(p["start"]))
        for period in sorted_periods:
            candidate = datetime.datetime.combine(
                target_date,
                _parse_time(period["start"]),
            ).replace(tzinfo=now.tzinfo)

            if candidate <= now:
                continue

            candidate_temp = period_temperatures.get(period.get("mode", ""))
            if candidate_temp is None:
                continue
            if candidate_temp > previous_temp:
                return candidate
            previous_temp = candidate_temp

    return None


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


# ---------------------------------------------------------------------------
# Dated presence / absence periods
# ---------------------------------------------------------------------------


def period_bounds(
    period: dict, tzinfo: datetime.tzinfo | None
) -> tuple[datetime.datetime, datetime.datetime]:
    """Return a period's (start, end) as aware datetimes.

    The bounds are local times ("YYYY-MM-DDTHH:MM") in the HA time zone,
    the one of `now`, like the time programs.
    """
    start = datetime.datetime.fromisoformat(period["start"])
    end = datetime.datetime.fromisoformat(period["end"])
    return start.replace(tzinfo=tzinfo), end.replace(tzinfo=tzinfo)


def period_covers(period: dict, person_id: str | None) -> bool:
    """True if the period applies to the person.

    A period without person_ids covers everyone. person_id=None asks for
    the household: only such periods cover it.
    """
    person_ids = period.get("person_ids")
    if person_ids is None:
        return True
    return person_id is not None and person_id in person_ids


def active_presence_period(
    periods: list | None,
    now: datetime.datetime,
    person_id: str | None = None,
) -> dict | None:
    """Return the period covering the person (or household) at now."""
    for period in periods or []:
        if not period_covers(period, person_id):
            continue
        start, end = period_bounds(period, now.tzinfo)
        if start <= now < end:
            return period
    return None


def presence_override(
    periods: list | None,
    now: datetime.datetime,
    person_id: str | None = None,
) -> bool | None:
    """Presence forced by a period at now: True, False, or None if none.

    person_id=None gives the household's: periods covering everyone only.
    """
    period = active_presence_period(periods, now, person_id)
    if period is None:
        return None
    return period["kind"] == PRESENCE_PERIOD_PRESENT


def absence_setback(period: dict) -> str:
    """The period a household absence holds: its setback, else Reduced."""
    return period.get("setback") or PERIOD_REDUCED


def household_setback(
    periods: list | None, now: datetime.datetime
) -> str | None:
    """Period held by the household absence at now, None without one."""
    period = active_presence_period(periods, now)
    if period is None or period["kind"] != PRESENCE_PERIOD_ABSENT:
        return None
    return absence_setback(period)


def _arrival_on_return(
    person_config: dict,
    ret: datetime.datetime,
    calendar_cache: dict | None,
    start_of_local_day,
) -> datetime.datetime | None:
    """When the person is home again once an absence ends at `ret`.

    The usual mode takes over: a schedule absent at the return gives its
    next present period; force_absent never; the other modes (HA, forced
    present, calendar) are assumed home on return.
    """
    mode = person_config.get("mode", PRESENCE_AUTOMATIC)
    if mode == PRESENCE_ABSENT:
        return None
    if mode == PRESENCE_AUTOMATIC:
        if resolve_presence(
            person_config, ret, calendar_cache, start_of_local_day
        ):
            return ret
        return next_occupied_at(
            person_config, ret, calendar_cache, start_of_local_day
        )
    return ret


def next_arrival(
    person_id: str,
    person_config: dict,
    periods: list | None,
    now: datetime.datetime,
    calendar_cache: dict | None = None,
    start_of_local_day=None,
) -> datetime.datetime | None:
    """Return the next time an away person comes home, periods included.

    - Inside an absence period: its return, or the usual mode's next
      arrival after it (see _arrival_on_return).
    - Inside a presence period: None (the person is home).
    - Otherwise the usual mode's next arrival (none for the HA and forced
      modes), unless a presence period starts first, and pushed to the
      return of an absence period it falls in.
    """
    active = active_presence_period(periods, now, person_id)
    if active is not None:
        if active["kind"] == PRESENCE_PERIOD_PRESENT:
            return None
        _, ret = period_bounds(active, now.tzinfo)
        return _arrival_on_return(
            person_config, ret, calendar_cache, start_of_local_day
        )

    arrival = next_occupied_at(
        person_config, now, calendar_cache, start_of_local_day
    )
    upcoming = sorted(
        (
            period_bounds(p, now.tzinfo) + (p["kind"],)
            for p in periods or []
            if period_covers(p, person_id)
        ),
        key=lambda bounds: bounds[0],
    )
    for start, end, kind in upcoming:
        if start <= now:
            continue
        if arrival is not None and arrival < start:
            break
        if kind == PRESENCE_PERIOD_PRESENT:
            return start
        if arrival is not None and arrival < end:
            arrival = _arrival_on_return(
                person_config, end, calendar_cache, start_of_local_day
            )
    return arrival


def has_presence_periods(
    periods: list | None,
    now: datetime.datetime,
    person_id: str,
) -> bool:
    """True if a period covering the person has not ended yet."""
    return any(
        period_covers(p, person_id) and period_bounds(p, now.tzinfo)[1] > now
        for p in periods or []
    )


def next_increase_with_absences(
    time_program: dict,
    period_temperatures: dict[str, float],
    periods: list | None,
    now: datetime.datetime,
) -> datetime.datetime | None:
    """Next zone setpoint increase, household absences included.

    During a household absence the zone holds the absence's setback
    (Reduced or Frost protection): its return is an increase when the
    program is warmer than that then, and an increase falling inside an
    absence does not happen.
    """

    def warmer_on_return(absence: dict, ret: datetime.datetime) -> bool:
        held = period_temperatures.get(absence_setback(absence))
        temp = period_temperatures.get(evaluate_schedule(time_program, ret))
        return temp is not None and (held is None or temp > held)

    def absence_at(t: datetime.datetime) -> dict | None:
        period = active_presence_period(periods, t)
        if period is None or period["kind"] != PRESENCE_PERIOD_ABSENT:
            return None
        return period

    t = now
    for _ in range(len(periods or []) + 1):
        absence = absence_at(t)
        if absence is None:
            candidate = next_setpoint_increase_at(
                time_program, period_temperatures, t
            )
            if candidate is None:
                return None
            absence = absence_at(candidate)
            if absence is None:
                return candidate
        _, ret = period_bounds(absence, now.tzinfo)
        if warmer_on_return(absence, ret):
            return ret
        t = ret
    return None


def validate_presence_periods(periods: list) -> tuple[bool, str]:
    """Validate the presence periods before saving them.

    Each period needs a unique id, a known kind, local "YYYY-MM-DDTHH:MM"
    bounds with the end after the start, and person_ids absent or a
    non-empty list. A setback is a known one, on an absence of everyone
    only. Two periods covering a common person (everyone covers all) must
    not overlap.
    """
    ids: set[str] = set()
    bounds: list[tuple] = []
    for i, period in enumerate(periods):
        period_id = period.get("id")
        if not isinstance(period_id, str) or not period_id:
            return False, f"period {i}: missing id"
        if period_id in ids:
            return False, f"period {i}: duplicate id {period_id!r}"
        ids.add(period_id)
        if period.get("kind") not in VALID_PRESENCE_PERIOD_KINDS:
            return False, f"period {i}: unknown kind {period.get('kind')!r}"
        if "setback" in period:
            if period["setback"] not in VALID_ABSENCE_SETBACKS:
                return False, (
                    f"period {i}: unknown setback {period['setback']!r}"
                )
            if (
                period["kind"] != PRESENCE_PERIOD_ABSENT
                or period.get("person_ids") is not None
            ):
                return False, (
                    f"period {i}: only an absence of everyone has a setback"
                )
        for key in ("start", "end"):
            value = period.get(key)
            if not isinstance(value, str) or not _LOCAL_DATETIME_RE.match(
                value
            ):
                return False, (
                    f"period {i}: '{key}' must be YYYY-MM-DDTHH:MM,"
                    f" got {value!r}"
                )
        try:
            start, end = period_bounds(period, None)
        except ValueError as err:
            return False, f"period {i}: {err}"
        if end <= start:
            return False, f"period {i}: the return must follow the start"
        person_ids = period.get("person_ids")
        if person_ids is not None and (
            not isinstance(person_ids, list)
            or not person_ids
            or not all(isinstance(p, str) for p in person_ids)
        ):
            return False, f"period {i}: person_ids must be a non-empty list"
        covered = None if person_ids is None else set(person_ids)
        for other_start, other_end, other_covered, j in bounds:
            shared = (
                covered is None
                or other_covered is None
                or covered & other_covered
            )
            if shared and start < other_end and other_start < end:
                return False, f"period {i} overlaps period {j}"
        bounds.append((start, end, covered, i))
    return True, ""

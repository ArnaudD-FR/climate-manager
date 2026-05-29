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
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    PRESENCE_ABSENT,
    PRESENCE_AUTOMATIC,
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
) -> bool:
    """Return True if the person is currently present.

    PERSON-02: Present mode → always True.
    PERSON-03: Absent mode → always False.
    PERSON-04: Automatic → evaluate person's periodic schedule.
    PERSON-05: Automatic + no schedule configured → False (absent by default).

    Missing 'mode' key defaults to PRESENCE_AUTOMATIC.
    The 'schedule' value is a per-day dict (D-01): {"mon": [...], ..., "sun": [...]}.
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
    active_state = "absent"  # default before first period
    for period in sorted_periods:
        period_start = _parse_time(period["start"])
        if current_time >= period_start:
            active_state = period["state"]
        else:
            break
    # Note: period schedule states are binary literals "present"/"absent" (PERSON-04),
    # NOT the presence mode constants PRESENCE_PRESENT/PRESENCE_ABSENT (D-21).
    return active_state == "present"


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
    last_nc_idx = today_periods.index(nc_periods[-1])
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

"""Climate Manager schedule and presence evaluation engine.

Pure Python — no Home Assistant imports.
All functions accept datetime objects directly; callers supply dt_util.now().

Requirements addressed:
- SCHED-01: global time program weekday groups with time periods
- SCHED-02: each period active from start until next period's start
- SCHED-03: last period of day ends at midnight (next day's group takes over)
- SCHED-04: each day in at most one weekday group (extended to exactly one by D-06)
- PERSON-01: presence modes (automatic, present, absent)
- PERSON-02: present mode → always True
- PERSON-03: absent mode → always False
- PERSON-04: automatic mode → evaluate person's periodic schedule
- PERSON-05: automatic + no schedule → False (absent by default)
- PERSON-07: present person → heat from first Normal/Comfort period to end of last
- PERSON-08: sandwiched Reduced/Frost between two N/C periods → hold preceding N/C temp
- PERSON-09: absent person → Reduced temperature
- GLOBAL-03: configurable period mode temperatures (caller provides period_temperatures)
- D-05: present + no N/C periods today → Reduced temperature
- D-06: programs must cover all 7 days with no duplicates
"""

import datetime
import logging

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

ALL_DAYS: set[str] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

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
    weekday_groups: list[dict],
    now: datetime.datetime,
) -> str:
    """Return the active period_mode for the current time.

    Algorithm:
    1. Find the weekday_group whose 'days' list contains today's weekday.
    2. Sort periods by start time ascending.
    3. Walk periods in order, keeping the last period whose start <= now.time()
       (>= comparison: exact boundary minute belongs to the new period — Pitfall 4).
    4. Return the active period's mode. If no period has started yet or no group
       covers today, return PERIOD_FROST_PROTECTION.

    SCHED-02: each period active from start until next period's start.
    SCHED-03: last period of day ends at midnight; next day's group takes over.
    """
    today = now.weekday()  # 0=Mon ... 6=Sun
    current_time = now.time()

    for group in weekday_groups:
        days = [DAY_TO_WEEKDAY[d] for d in group["days"]]
        if today not in days:
            continue
        # Found today's group — find active period.
        # WR-01: log which group is used so "first match wins" is surfaced in debug logs.
        _LOGGER.debug("evaluate_schedule: using first matching group for today (%s)", today)
        periods = sorted(group["periods"], key=lambda p: p["start"])
        active_mode = None
        for period in periods:
            period_start = _parse_time(period["start"])
            if current_time >= period_start:
                active_mode = period["mode"]
            else:
                break
        return active_mode if active_mode is not None else PERIOD_FROST_PROTECTION

    return PERIOD_FROST_PROTECTION  # No group covers today (should not happen after D-06)


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
    """
    mode = person_config.get("mode", PRESENCE_AUTOMATIC)

    if mode == PRESENCE_PRESENT:
        return True
    if mode == PRESENCE_ABSENT:
        return False

    # Automatic: evaluate periodic schedule
    schedule = person_config.get("schedule", {})
    weekday_groups = schedule.get("weekday_groups", [])
    if not weekday_groups:
        return False  # PERSON-05: no schedule → absent

    today = now.weekday()
    current_time = now.time()

    for group in weekday_groups:
        days = [DAY_TO_WEEKDAY[d] for d in group["days"]]
        if today not in days:
            continue
        # Found today's group — find active presence state
        periods = sorted(group["periods"], key=lambda p: p["start"])
        active_state = "absent"  # default before first period
        for period in periods:
            period_start = _parse_time(period["start"])
            if current_time >= period_start:
                active_state = period["state"]
            else:
                break
        return active_state == PRESENCE_PRESENT

    return False  # No group covers today


def compute_occupied_temp(
    weekday_groups: list[dict],
    now: datetime.datetime,
    is_present: bool,
    period_temperatures: dict[str, float],
) -> float:
    """Return the desired temperature for a person-associated room.

    PERSON-07: present → heat continuously from first Normal/Comfort period
               to end of last Normal/Comfort period of the day.
    PERSON-08: sandwiched Reduced/Frost period between two N/C periods
               → hold temperature of the preceding Normal/Comfort period (gap-fill).
    PERSON-09: absent → PERIOD_REDUCED temperature always.
    D-05: present + today has no Normal/Comfort periods → PERIOD_REDUCED temperature.
    """
    if not is_present:
        return period_temperatures[PERIOD_REDUCED]

    today = now.weekday()
    current_time = now.time()

    # Find today's periods
    today_periods: list[dict] = []
    for group in weekday_groups:
        days = [DAY_TO_WEEKDAY[d] for d in group["days"]]
        if today in days:
            today_periods = sorted(group["periods"], key=lambda p: p["start"])
            break

    # Identify Normal/Comfort periods
    nc_modes = {PERIOD_NORMAL, PERIOD_COMFORT}
    nc_periods = [p for p in today_periods if p["mode"] in nc_modes]

    if not nc_periods:
        # D-05: no Normal/Comfort periods at all → apply Reduced
        _LOGGER.debug(
            "compute_occupied_temp: no periods for today (%s) — returning Reduced for present person",
            today,
        )
        return period_temperatures[PERIOD_REDUCED]

    # Occupied window: [start of first N/C, start of period after last N/C]
    first_nc_start = _parse_time(nc_periods[0]["start"])

    # End of occupied window = start of the period immediately after the last N/C,
    # or None if the last N/C is the final period of the day (window extends to midnight).
    last_nc_idx = today_periods.index(nc_periods[-1])
    if last_nc_idx + 1 < len(today_periods):
        occupied_end: datetime.time | None = _parse_time(today_periods[last_nc_idx + 1]["start"])
    else:
        occupied_end = None  # last N/C is last period — window extends to midnight

    # Before the occupied window → Reduced
    if current_time < first_nc_start:
        return period_temperatures[PERIOD_REDUCED]

    # After the occupied window → Reduced
    if occupied_end is not None and current_time >= occupied_end:
        return period_temperatures[PERIOD_REDUCED]

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

    return period_temperatures.get(active_mode, period_temperatures[PERIOD_REDUCED])


def validate_7day_coverage(
    weekday_groups: list[dict],
) -> tuple[bool, str]:
    """Validate that exactly all 7 days are covered, with no duplicates.

    Returns (True, '') if valid, (False, error_message) if invalid.
    Called at config save time (Phase 3 WebSocket handler) and exercised by unit tests.

    D-06: programs must cover all 7 days (Mon–Sun). Each day must appear in
    exactly one weekday group. Applies to both global and per-room programs.
    """
    covered: list[str] = []
    for group in weekday_groups:
        covered.extend(group.get("days", []))

    covered_set = set(covered)

    # Check for duplicates first
    if len(covered) != len(covered_set):
        return False, "Duplicate day assignment in weekday groups"

    # Check for missing or unknown days
    if covered_set != ALL_DAYS:
        missing = ALL_DAYS - covered_set
        extra = covered_set - ALL_DAYS
        msg_parts = []
        if missing:
            msg_parts.append(f"Missing days: {sorted(missing)}")
        if extra:
            msg_parts.append(f"Unknown days: {sorted(extra)}")
        return False, "; ".join(msg_parts)

    return True, ""

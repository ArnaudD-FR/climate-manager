"""Tests for schedule.py — pure Python schedule evaluation functions.

No hass fixture needed. Functions accept datetime objects directly.
Tests:
- evaluate_schedule: finds active period for current time (SCHED-01..04)
- validate_daily_program: rejects missing/unknown day keys (D-01)
- resolve_presence: PERSON-01 through PERSON-05 modes
- resolve_presence: even/odd week selection (SCHED-02, SCHED-03)
- compute_occupied_temp: PERSON-07/08/09 occupied window and gap-fill
"""

import datetime


from custom_components.climate_manager.schedule import (
    ALL_DAYS,
    DAY_TO_WEEKDAY,
    WEEKDAY_TO_DAY,
    compute_occupied_temp,
    evaluate_schedule,
    resolve_presence,
    validate_daily_program,
)
from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    PERIOD_FROST_PROTECTION,
    PERIOD_REDUCED,
    PERIOD_NORMAL,
    PERIOD_COMFORT,
    PRESENCE_AUTOMATIC,
    PRESENCE_PRESENT,
    PRESENCE_ABSENT,
)

# ---------------------------------------------------------------------------
# Module-level fixture constants (per-day dict schema — D-01)
# ---------------------------------------------------------------------------

# Standard weekday program: Mon–Fri with Normal/Reduced, Sat–Sun with Comfort
WEEKDAY_PROGRAM: dict = {
    "mon": [
        {"start": "07:00", "mode": "normal"},
        {"start": "22:00", "mode": "reduced"},
    ],
    "tue": [
        {"start": "07:00", "mode": "normal"},
        {"start": "22:00", "mode": "reduced"},
    ],
    "wed": [
        {"start": "07:00", "mode": "normal"},
        {"start": "22:00", "mode": "reduced"},
    ],
    "thu": [
        {"start": "07:00", "mode": "normal"},
        {"start": "22:00", "mode": "reduced"},
    ],
    "fri": [
        {"start": "07:00", "mode": "normal"},
        {"start": "22:00", "mode": "reduced"},
    ],
    "sat": [
        {"start": "08:00", "mode": "comfort"},
        {"start": "23:00", "mode": "reduced"},
    ],
    "sun": [
        {"start": "08:00", "mode": "comfort"},
        {"start": "23:00", "mode": "reduced"},
    ],
}

# Full 7-day program used for compute_occupied_temp tests
# Schedule: 00:00 frost, 07:00 normal, 12:00 reduced, 14:00 comfort, 22:00 reduced
FULL_WEEK_PROGRAM: dict = {
    day: [
        {"start": "00:00", "mode": "frost_protection"},
        {"start": "07:00", "mode": "normal"},
        {"start": "12:00", "mode": "reduced"},
        {"start": "14:00", "mode": "comfort"},
        {"start": "22:00", "mode": "reduced"},
    ]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}

# Presence schedule: Mon–Fri present 08:00–22:00, absent otherwise; Sat–Sun absent
PERSON_SCHEDULE: dict = {
    "mon": [
        {"start": "00:00", "state": "absent"},
        {"start": "08:00", "state": "present"},
        {"start": "22:00", "state": "absent"},
    ],
    "tue": [
        {"start": "00:00", "state": "absent"},
        {"start": "08:00", "state": "present"},
        {"start": "22:00", "state": "absent"},
    ],
    "wed": [
        {"start": "00:00", "state": "absent"},
        {"start": "08:00", "state": "present"},
        {"start": "22:00", "state": "absent"},
    ],
    "thu": [
        {"start": "00:00", "state": "absent"},
        {"start": "08:00", "state": "present"},
        {"start": "22:00", "state": "absent"},
    ],
    "fri": [
        {"start": "00:00", "state": "absent"},
        {"start": "08:00", "state": "present"},
        {"start": "22:00", "state": "absent"},
    ],
    "sat": [{"start": "00:00", "state": "absent"}],
    "sun": [{"start": "00:00", "state": "absent"}],
}

# All-days-present schedule for even_odd tests (SCHED-02)
ALWAYS_PRESENT_SCHEDULE: dict = {
    day: [{"start": "00:00", "state": "present"}] for day in ALL_DAYS
}

# All-days-absent schedule for even_odd tests (SCHED-02)
ALWAYS_ABSENT_SCHEDULE: dict = {
    day: [{"start": "00:00", "state": "absent"}] for day in ALL_DAYS
}

# Default period temperatures (from const.py DEFAULT_PERIOD_TEMPERATURES)
TEMPS = DEFAULT_PERIOD_TEMPERATURES


# ---------------------------------------------------------------------------
# evaluate_schedule tests
# ---------------------------------------------------------------------------


def test_evaluate_schedule_returns_normal_at_0830_monday():
    """Monday 08:30 with a weekday program that starts at 07:00 normal → normal."""
    now = datetime.datetime(
        2026, 1, 5, 8, 30, tzinfo=datetime.timezone.utc
    )  # Monday
    assert now.weekday() == 0  # Sanity check: this is Monday
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_NORMAL


def test_evaluate_schedule_boundary_at_exact_start_time_pitfall4():
    """Pitfall 4 regression: at exactly 07:00 the period boundary is inclusive (>=).

    The period defined as {"start": "07:00", "mode": "normal"} must be active
    at exactly 07:00:00 — not one minute later.
    """
    now = datetime.datetime(
        2026, 1, 5, 7, 0, tzinfo=datetime.timezone.utc
    )  # Monday 07:00
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_NORMAL, (
        "Period boundary must use >= so 07:00 exact returns normal, not the prior mode"
    )


def test_evaluate_schedule_before_first_period_returns_frost_protection():
    """Before the first period of the day → PERIOD_FROST_PROTECTION."""
    now = datetime.datetime(
        2026, 1, 5, 6, 59, tzinfo=datetime.timezone.utc
    )  # Monday 06:59
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_FROST_PROTECTION


def test_evaluate_schedule_returns_reduced_at_2200():
    """At exactly 22:00 on a weekday → reduced period (>=, Pitfall 4)."""
    now = datetime.datetime(
        2026, 1, 5, 22, 0, tzinfo=datetime.timezone.utc
    )  # Monday 22:00
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_REDUCED


def test_evaluate_schedule_weekend_uses_correct_group():
    """Saturday should resolve from the sat key, not the weekday keys."""
    now = datetime.datetime(
        2026, 1, 10, 10, 0, tzinfo=datetime.timezone.utc
    )  # Saturday
    assert now.weekday() == 5  # Sanity check: Saturday
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_COMFORT


def test_evaluate_schedule_missing_day_key_returns_frost_protection():
    """If the per-day dict has no entry for today → PERIOD_FROST_PROTECTION (SCHED-03 fallback)."""
    # Only Monday is covered
    partial_program = {
        "mon": [{"start": "07:00", "mode": "normal"}],
    }
    now = datetime.datetime(
        2026, 1, 6, 10, 0, tzinfo=datetime.timezone.utc
    )  # Tuesday
    result = evaluate_schedule(partial_program, now)
    assert result == PERIOD_FROST_PROTECTION


def test_evaluate_schedule_empty_daily_program_returns_frost_protection():
    """Empty per-day dict (all days []) → PERIOD_FROST_PROTECTION."""
    empty_program = {
        d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    result = evaluate_schedule(empty_program, now)
    assert result == PERIOD_FROST_PROTECTION


# ---------------------------------------------------------------------------
# validate_daily_program tests (D-01)
# ---------------------------------------------------------------------------


def test_validate_daily_program_valid_full_week():
    """A per-day dict with all 7 day keys → (True, '')."""
    ok, msg = validate_daily_program(WEEKDAY_PROGRAM)
    assert ok is True
    assert msg == ""


def test_validate_daily_program_missing_day_returns_false():
    """A dict missing 'sun' → (False, message naming sun)."""
    program_missing_sun = {
        d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat"]
    }
    ok, msg = validate_daily_program(program_missing_sun)
    assert ok is False
    assert "sun" in msg or "Missing" in msg


def test_validate_daily_program_unknown_day_key_returns_false():
    """A dict with an unknown key 'xyz' → (False, message naming xyz)."""
    program_bad = {
        d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    program_bad["xyz"] = []
    ok, msg = validate_daily_program(program_bad)
    assert ok is False
    assert "xyz" in msg or "Unknown" in msg


def test_validate_daily_program_empty_dict_returns_false():
    """Empty dict → all 7 days missing → (False, ...)."""
    ok, msg = validate_daily_program({})
    assert ok is False
    assert "Missing" in msg


def test_validate_daily_program_all_empty_lists_valid():
    """Dict with all 7 day keys and empty lists is valid."""
    program_empty = {
        d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    ok, msg = validate_daily_program(program_empty)
    assert ok is True
    assert msg == ""


def test_validate_daily_program_missing_and_unknown_returns_false():
    """Dict missing 'sun' but has 'xyz' → (False, both in message)."""
    program = {d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat"]}
    program["xyz"] = []
    ok, msg = validate_daily_program(program)
    assert ok is False


# ---------------------------------------------------------------------------
# resolve_presence tests (PERSON-01 through PERSON-05)
# ---------------------------------------------------------------------------


def test_resolve_presence_present_mode_always_true():
    """PERSON-02: mode 'present' → True regardless of time."""
    config = {"mode": PRESENCE_PRESENT}
    now = datetime.datetime(
        2026, 1, 5, 3, 0, tzinfo=datetime.timezone.utc
    )  # Monday 03:00
    assert resolve_presence(config, now) is True


def test_resolve_presence_absent_mode_always_false():
    """PERSON-03: mode 'absent' → False regardless of time."""
    config = {"mode": PRESENCE_ABSENT}
    now = datetime.datetime(
        2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc
    )  # Monday noon
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_empty_schedule_returns_false():
    """PERSON-05: automatic mode + empty schedule dict → False (absent by default)."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": {}}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_no_schedule_key_returns_false():
    """PERSON-05: automatic mode + no schedule key → False."""
    config = {"mode": PRESENCE_AUTOMATIC}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_missing_mode_defaults_to_automatic():
    """Missing 'mode' key defaults to automatic behavior."""
    config = {"schedule": {}}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    # No mode key → defaults to automatic → empty schedule → False
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_during_present_period():
    """PERSON-04: automatic mode, schedule says present at current time → True."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(
        2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc
    )  # Monday 10:00
    assert resolve_presence(config, now) is True


def test_resolve_presence_automatic_during_absent_period():
    """PERSON-04: automatic mode, schedule says absent at current time → False."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(
        2026, 1, 5, 6, 0, tzinfo=datetime.timezone.utc
    )  # Monday 06:00
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_missing_day_in_schedule_returns_false():
    """Automatic mode: day not in per-day schedule dict → False."""
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule": {
            "mon": [{"start": "08:00", "state": "present"}],
            # tue missing
        },
    }
    now = datetime.datetime(
        2026, 1, 6, 10, 0, tzinfo=datetime.timezone.utc
    )  # Tuesday
    assert resolve_presence(config, now) is False


# ---------------------------------------------------------------------------
# resolve_presence tests — even/odd week selection (SCHED-02, SCHED-03)
# ---------------------------------------------------------------------------


def test_resolve_presence_even_odd_even_week_uses_schedule_even():
    """SCHED-02: ISO week 2 (2026-01-05, Mon) parity 0 → even → schedule_even."""
    # 2026-01-05 = ISO week 2, parity 0 (even)
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert now.date().isocalendar().week % 2 == 0  # Sanity: even week
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "even_odd",
        "schedule_even": ALWAYS_PRESENT_SCHEDULE,
        "schedule_odd": ALWAYS_ABSENT_SCHEDULE,
    }
    assert resolve_presence(config, now) is True  # even week → present


def test_resolve_presence_even_odd_odd_week_uses_schedule_odd():
    """SCHED-02: ISO week 3 (2026-01-12, Mon) parity 1 → odd → schedule_odd."""
    # 2026-01-12 = ISO week 3, parity 1 (odd)
    now = datetime.datetime(2026, 1, 12, 10, 0, tzinfo=datetime.timezone.utc)
    assert now.date().isocalendar().week % 2 == 1  # Sanity: odd week
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "even_odd",
        "schedule_even": ALWAYS_PRESENT_SCHEDULE,
        "schedule_odd": ALWAYS_ABSENT_SCHEDULE,
    }
    assert resolve_presence(config, now) is False  # odd week → absent


def test_resolve_presence_no_schedule_type_uses_schedule():
    """SCHED-03: absent schedule_type defaults to single — uses schedule key."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is True


def test_resolve_presence_explicit_single_uses_schedule():
    """SCHED-02: explicit schedule_type='single' selects schedule key."""
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "single",
        "schedule": PERSON_SCHEDULE,
    }
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is True


def test_resolve_presence_even_odd_missing_week_schedule_returns_false():
    """PERSON-05 + SCHED-02: even_odd with no schedule_even key → {} → absent."""
    # ISO week 2 → even → looks for schedule_even → not found → {} → absent
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    config = {"mode": PRESENCE_AUTOMATIC, "schedule_type": "even_odd"}
    # No schedule_even key at all → .get("schedule_even", {}) → no periods
    assert resolve_presence(config, now) is False


# ---------------------------------------------------------------------------
# compute_occupied_temp tests (PERSON-07/08/09, D-05)
# ---------------------------------------------------------------------------


def test_compute_occupied_temp_absent_returns_reduced():
    """PERSON-09: absent person → PERIOD_REDUCED temperature regardless of schedule."""
    now = datetime.datetime(
        2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc
    )  # Monday 10:00
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=False, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_REDUCED]
    assert period == PERIOD_REDUCED


def test_compute_occupied_temp_present_no_nc_periods_returns_reduced():
    """D-05: present + today has no Normal/Comfort periods → PERIOD_REDUCED temperature."""
    frost_only_program = {
        day: [
            {"start": "00:00", "mode": "frost_protection"},
            {"start": "08:00", "mode": "reduced"},
        ]
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    temp, period = compute_occupied_temp(
        frost_only_program, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_REDUCED]
    assert period == PERIOD_REDUCED


def test_compute_occupied_temp_present_before_first_nc_period():
    """Present but before the first Normal/Comfort period of the day → Reduced temp."""
    # FULL_WEEK_PROGRAM: first N/C period starts at 07:00 (normal)
    now = datetime.datetime(
        2026, 1, 5, 6, 30, tzinfo=datetime.timezone.utc
    )  # Monday 06:30
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_REDUCED]
    assert period == PERIOD_REDUCED


def test_compute_occupied_temp_present_after_last_nc_period_end():
    """Present but after the end of last N/C period → Reduced temp.

    FULL_WEEK_PROGRAM: last N/C period is comfort (14:00–22:00).
    After 22:00 (the period following the last N/C) → Reduced.
    """
    now = datetime.datetime(
        2026, 1, 5, 22, 30, tzinfo=datetime.timezone.utc
    )  # Monday 22:30
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_REDUCED]
    assert period == PERIOD_REDUCED


def test_compute_occupied_temp_present_during_normal_period():
    """PERSON-07: present during a Normal period within the occupied window → Normal temp."""
    # FULL_WEEK_PROGRAM: 07:00 normal
    now = datetime.datetime(
        2026, 1, 5, 8, 0, tzinfo=datetime.timezone.utc
    )  # Monday 08:00
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_NORMAL]
    assert period == PERIOD_NORMAL


def test_compute_occupied_temp_present_during_comfort_period():
    """PERSON-07: present during a Comfort period within the occupied window → Comfort temp."""
    # FULL_WEEK_PROGRAM: 14:00 comfort
    now = datetime.datetime(
        2026, 1, 5, 15, 0, tzinfo=datetime.timezone.utc
    )  # Monday 15:00
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_COMFORT]
    assert period == PERIOD_COMFORT


def test_compute_occupied_temp_person08_sandwiched_reduced_returns_preceding_nc_temp():
    """PERSON-08: present during a Reduced period sandwiched between two N/C periods
    → returns the temperature of the preceding Normal period (gap-fill).

    Schedule: 07:00 normal, 12:00 reduced, 14:00 comfort, 22:00 reduced
    At 12:30 (active period: reduced, preceded by normal) → Normal temperature.
    """
    now = datetime.datetime(
        2026, 1, 5, 12, 30, tzinfo=datetime.timezone.utc
    )  # Monday 12:30
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_NORMAL], (
        "Sandwiched Reduced period should return preceding Normal temperature (PERSON-08 gap-fill)"
    )
    assert period == PERIOD_NORMAL


def test_compute_occupied_temp_person08_after_last_nc_returns_reduced():
    """PERSON-08 boundary: at 22:30 (after last N/C comfort ends at 22:00)
    → Reduced temperature, not gap-filled.

    Schedule ends with: 22:00 reduced (after 14:00 comfort).
    22:30 is outside the occupied window → Reduced.
    """
    now = datetime.datetime(
        2026, 1, 5, 22, 30, tzinfo=datetime.timezone.utc
    )  # Monday 22:30
    temp, period = compute_occupied_temp(
        FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_REDUCED]
    assert period == PERIOD_REDUCED


def test_compute_occupied_temp_present_empty_program_returns_reduced():
    """Present but empty per-day program (all days []) → Reduced (no N/C periods)."""
    empty_program = {
        d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    temp, period = compute_occupied_temp(
        empty_program, now, is_present=True, period_temperatures=TEMPS
    )
    assert temp == TEMPS[PERIOD_REDUCED]
    assert period == PERIOD_REDUCED


# ---------------------------------------------------------------------------
# Module-level constant tests
# ---------------------------------------------------------------------------


def test_day_to_weekday_mapping():
    """DAY_TO_WEEKDAY maps all 7 day tokens to correct Python weekday() integers."""
    assert DAY_TO_WEEKDAY["mon"] == 0
    assert DAY_TO_WEEKDAY["tue"] == 1
    assert DAY_TO_WEEKDAY["wed"] == 2
    assert DAY_TO_WEEKDAY["thu"] == 3
    assert DAY_TO_WEEKDAY["fri"] == 4
    assert DAY_TO_WEEKDAY["sat"] == 5
    assert DAY_TO_WEEKDAY["sun"] == 6


def test_weekday_to_day_mapping():
    """WEEKDAY_TO_DAY maps Python weekday() integers to day name strings."""
    assert WEEKDAY_TO_DAY[0] == "mon"
    assert WEEKDAY_TO_DAY[1] == "tue"
    assert WEEKDAY_TO_DAY[2] == "wed"
    assert WEEKDAY_TO_DAY[3] == "thu"
    assert WEEKDAY_TO_DAY[4] == "fri"
    assert WEEKDAY_TO_DAY[5] == "sat"
    assert WEEKDAY_TO_DAY[6] == "sun"


def test_all_days_set():
    """ALL_DAYS contains exactly the 7 canonical day tokens."""
    assert ALL_DAYS == {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

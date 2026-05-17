"""Tests for schedule.py — pure Python schedule evaluation functions.

No hass fixture needed. Functions accept datetime objects directly.
Tests:
- evaluate_schedule: finds active period for current time (SCHED-01..04)
- validate_7day_coverage: rejects missing/duplicate days (D-06)
- resolve_presence: PERSON-01 through PERSON-05 modes
- compute_occupied_temp: PERSON-07/08/09 occupied window and gap-fill
"""

import datetime

import pytest

from custom_components.climate_manager.schedule import (
    ALL_DAYS,
    DAY_TO_WEEKDAY,
    compute_occupied_temp,
    evaluate_schedule,
    resolve_presence,
    validate_7day_coverage,
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
# Module-level fixture constants (mirror test_trv.py module-constant style)
# ---------------------------------------------------------------------------

# Standard weekday program: Mon–Fri with Normal/Reduced, Sat–Sun with Comfort
WEEKDAY_PROGRAM = [
    {
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "periods": [
            {"start": "07:00", "mode": "normal"},
            {"start": "22:00", "mode": "reduced"},
        ],
    },
    {
        "days": ["sat", "sun"],
        "periods": [
            {"start": "08:00", "mode": "comfort"},
            {"start": "23:00", "mode": "reduced"},
        ],
    },
]

# Full 7-day program used for compute_occupied_temp tests
# Schedule: 07:00 normal, 12:00 reduced, 14:00 comfort, 22:00 reduced
FULL_WEEK_PROGRAM = [
    {
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "periods": [
            {"start": "00:00", "mode": "frost_protection"},
            {"start": "07:00", "mode": "normal"},
            {"start": "12:00", "mode": "reduced"},
            {"start": "14:00", "mode": "comfort"},
            {"start": "22:00", "mode": "reduced"},
        ],
    }
]

# Presence schedule: Mon–Fri present 08:00–22:00, absent otherwise
PERSON_SCHEDULE = {
    "weekday_groups": [
        {
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "periods": [
                {"start": "00:00", "state": "absent"},
                {"start": "08:00", "state": "present"},
                {"start": "22:00", "state": "absent"},
            ],
        },
        {
            "days": ["sat", "sun"],
            "periods": [
                {"start": "00:00", "state": "absent"},
            ],
        },
    ]
}

# Default period temperatures (from const.py DEFAULT_PERIOD_TEMPERATURES)
TEMPS = DEFAULT_PERIOD_TEMPERATURES


# ---------------------------------------------------------------------------
# evaluate_schedule tests
# ---------------------------------------------------------------------------


def test_evaluate_schedule_returns_normal_at_0830_monday():
    """Monday 08:30 with a weekday group that starts at 07:00 normal → normal."""
    now = datetime.datetime(2026, 1, 5, 8, 30, tzinfo=datetime.timezone.utc)  # Monday
    assert now.weekday() == 0  # Sanity check: this is Monday
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_NORMAL


def test_evaluate_schedule_boundary_at_exact_start_time_pitfall4():
    """Pitfall 4 regression: at exactly 07:00 the period boundary is inclusive (>=).

    The period defined as {"start": "07:00", "mode": "normal"} must be active
    at exactly 07:00:00 — not one minute later.
    """
    now = datetime.datetime(2026, 1, 5, 7, 0, tzinfo=datetime.timezone.utc)  # Monday 07:00
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_NORMAL, (
        "Period boundary must use >= so 07:00 exact returns normal, not the prior mode"
    )


def test_evaluate_schedule_before_first_period_returns_frost_protection():
    """Before the first period of the day → PERIOD_FROST_PROTECTION."""
    now = datetime.datetime(2026, 1, 5, 6, 59, tzinfo=datetime.timezone.utc)  # Monday 06:59
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_FROST_PROTECTION


def test_evaluate_schedule_returns_reduced_at_2200():
    """At exactly 22:00 on a weekday → reduced period (>=, Pitfall 4)."""
    now = datetime.datetime(2026, 1, 5, 22, 0, tzinfo=datetime.timezone.utc)  # Monday 22:00
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_REDUCED


def test_evaluate_schedule_weekend_uses_correct_group():
    """Saturday should resolve from the sat/sun group, not the weekday group."""
    now = datetime.datetime(2026, 1, 10, 10, 0, tzinfo=datetime.timezone.utc)  # Saturday
    assert now.weekday() == 5  # Sanity check: Saturday
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)
    assert result == PERIOD_COMFORT


def test_evaluate_schedule_no_group_covers_today_returns_frost_protection():
    """If no weekday_group contains today → PERIOD_FROST_PROTECTION (SCHED-03 fallback)."""
    # Only Monday is covered
    partial_program = [
        {
            "days": ["mon"],
            "periods": [{"start": "07:00", "mode": "normal"}],
        }
    ]
    now = datetime.datetime(2026, 1, 6, 10, 0, tzinfo=datetime.timezone.utc)  # Tuesday
    result = evaluate_schedule(partial_program, now)
    assert result == PERIOD_FROST_PROTECTION


def test_evaluate_schedule_empty_weekday_groups_returns_frost_protection():
    """Empty weekday_groups list → PERIOD_FROST_PROTECTION."""
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    result = evaluate_schedule([], now)
    assert result == PERIOD_FROST_PROTECTION


# ---------------------------------------------------------------------------
# validate_7day_coverage tests (D-06)
# ---------------------------------------------------------------------------


def test_validate_7day_coverage_valid_full_week():
    """A program covering all 7 days with no duplicates → (True, '')."""
    ok, msg = validate_7day_coverage(WEEKDAY_PROGRAM)
    assert ok is True
    assert msg == ""


def test_validate_7day_coverage_missing_day_returns_false():
    """A program missing Saturday → (False, message naming sat)."""
    program_missing_sat = [
        {
            "days": ["mon", "tue", "wed", "thu", "fri", "sun"],
            "periods": [{"start": "07:00", "mode": "normal"}],
        }
    ]
    ok, msg = validate_7day_coverage(program_missing_sat)
    assert ok is False
    assert "sat" in msg.lower() or "Missing" in msg


def test_validate_7day_coverage_duplicate_day_returns_false():
    """A program with mon duplicated → (False, duplicate message)."""
    program_dup = [
        {
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "periods": [{"start": "07:00", "mode": "normal"}],
        },
        {
            "days": ["mon", "sat", "sun"],  # mon appears twice
            "periods": [{"start": "08:00", "mode": "comfort"}],
        },
    ]
    ok, msg = validate_7day_coverage(program_dup)
    assert ok is False
    assert "uplicate" in msg or "duplicate" in msg.lower()


def test_validate_7day_coverage_unknown_day_token_returns_false():
    """Unknown day token like 'xyz' → (False, unknown-days message)."""
    program_bad = [
        {
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "xyz"],
            "periods": [{"start": "07:00", "mode": "normal"}],
        }
    ]
    ok, msg = validate_7day_coverage(program_bad)
    assert ok is False
    assert "xyz" in msg or "Unknown" in msg or "unknown" in msg.lower()


def test_validate_7day_coverage_single_group_full_week():
    """A single group with all 7 days is valid."""
    program_single = [
        {
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "periods": [{"start": "00:00", "mode": "frost_protection"}],
        }
    ]
    ok, msg = validate_7day_coverage(program_single)
    assert ok is True
    assert msg == ""


def test_validate_7day_coverage_empty_groups_returns_false():
    """Empty weekday_groups → all 7 days missing."""
    ok, msg = validate_7day_coverage([])
    assert ok is False


# ---------------------------------------------------------------------------
# resolve_presence tests (PERSON-01 through PERSON-05)
# ---------------------------------------------------------------------------


def test_resolve_presence_present_mode_always_true():
    """PERSON-02: mode 'present' → True regardless of time."""
    config = {"mode": PRESENCE_PRESENT}
    now = datetime.datetime(2026, 1, 5, 3, 0, tzinfo=datetime.timezone.utc)  # Monday 03:00
    assert resolve_presence(config, now) is True


def test_resolve_presence_absent_mode_always_false():
    """PERSON-03: mode 'absent' → False regardless of time."""
    config = {"mode": PRESENCE_ABSENT}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)  # Monday noon
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_empty_schedule_returns_false():
    """PERSON-05: automatic mode + no weekday_groups → False (absent by default)."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": {"weekday_groups": []}}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_no_schedule_key_returns_false():
    """PERSON-05: automatic mode + no schedule key → False."""
    config = {"mode": PRESENCE_AUTOMATIC}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_missing_mode_defaults_to_automatic():
    """Missing 'mode' key defaults to automatic behavior."""
    config = {"schedule": {"weekday_groups": []}}
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    # No mode key → defaults to automatic → empty schedule → False
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_during_present_period():
    """PERSON-04: automatic mode, schedule says present at current time → True."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)  # Monday 10:00
    assert resolve_presence(config, now) is True


def test_resolve_presence_automatic_during_absent_period():
    """PERSON-04: automatic mode, schedule says absent at current time → False."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(2026, 1, 5, 6, 0, tzinfo=datetime.timezone.utc)  # Monday 06:00
    assert resolve_presence(config, now) is False


def test_resolve_presence_automatic_no_group_covers_today_returns_false():
    """Automatic mode: no group covers today → False."""
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule": {
            "weekday_groups": [
                {
                    "days": ["mon"],
                    "periods": [{"start": "08:00", "state": "present"}],
                }
            ]
        },
    }
    now = datetime.datetime(2026, 1, 6, 10, 0, tzinfo=datetime.timezone.utc)  # Tuesday
    assert resolve_presence(config, now) is False


# ---------------------------------------------------------------------------
# compute_occupied_temp tests (PERSON-07/08/09, D-05)
# ---------------------------------------------------------------------------


def test_compute_occupied_temp_absent_returns_reduced():
    """PERSON-09: absent person → PERIOD_REDUCED temperature regardless of schedule."""
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)  # Monday 10:00
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=False, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_REDUCED]


def test_compute_occupied_temp_present_no_nc_periods_returns_reduced():
    """D-05: present + today has no Normal/Comfort periods → PERIOD_REDUCED temperature."""
    frost_only_program = [
        {
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "periods": [
                {"start": "00:00", "mode": "frost_protection"},
                {"start": "08:00", "mode": "reduced"},
            ],
        }
    ]
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    result = compute_occupied_temp(frost_only_program, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_REDUCED]


def test_compute_occupied_temp_present_before_first_nc_period():
    """Present but before the first Normal/Comfort period of the day → Reduced temp."""
    # FULL_WEEK_PROGRAM: first N/C period starts at 07:00 (normal)
    now = datetime.datetime(2026, 1, 5, 6, 30, tzinfo=datetime.timezone.utc)  # Monday 06:30
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_REDUCED]


def test_compute_occupied_temp_present_after_last_nc_period_end():
    """Present but after the end of last N/C period → Reduced temp.

    FULL_WEEK_PROGRAM: last N/C period is comfort (14:00–22:00).
    After 22:00 (the period following the last N/C) → Reduced.
    """
    now = datetime.datetime(2026, 1, 5, 22, 30, tzinfo=datetime.timezone.utc)  # Monday 22:30
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_REDUCED]


def test_compute_occupied_temp_present_during_normal_period():
    """PERSON-07: present during a Normal period within the occupied window → Normal temp."""
    # FULL_WEEK_PROGRAM: 07:00 normal
    now = datetime.datetime(2026, 1, 5, 8, 0, tzinfo=datetime.timezone.utc)  # Monday 08:00
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_NORMAL]


def test_compute_occupied_temp_present_during_comfort_period():
    """PERSON-07: present during a Comfort period within the occupied window → Comfort temp."""
    # FULL_WEEK_PROGRAM: 14:00 comfort
    now = datetime.datetime(2026, 1, 5, 15, 0, tzinfo=datetime.timezone.utc)  # Monday 15:00
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_COMFORT]


def test_compute_occupied_temp_person08_sandwiched_reduced_returns_preceding_nc_temp():
    """PERSON-08: present during a Reduced period sandwiched between two N/C periods
    → returns the temperature of the preceding Normal period (gap-fill).

    Schedule: 07:00 normal, 12:00 reduced, 14:00 comfort, 22:00 reduced
    At 12:30 (active period: reduced, preceded by normal) → Normal temperature.
    """
    now = datetime.datetime(2026, 1, 5, 12, 30, tzinfo=datetime.timezone.utc)  # Monday 12:30
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_NORMAL], (
        "Sandwiched Reduced period should return preceding Normal temperature (PERSON-08 gap-fill)"
    )


def test_compute_occupied_temp_person08_after_last_nc_returns_reduced():
    """PERSON-08 boundary: at 22:30 (after last N/C comfort ends at 22:00)
    → Reduced temperature, not gap-filled.

    Schedule ends with: 22:00 reduced (after 14:00 comfort).
    22:30 is outside the occupied window → Reduced.
    """
    now = datetime.datetime(2026, 1, 5, 22, 30, tzinfo=datetime.timezone.utc)  # Monday 22:30
    result = compute_occupied_temp(FULL_WEEK_PROGRAM, now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_REDUCED]


def test_compute_occupied_temp_present_empty_groups_returns_reduced():
    """Present but empty weekday_groups → Reduced (no schedule = no N/C periods)."""
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    result = compute_occupied_temp([], now, is_present=True, period_temperatures=TEMPS)
    assert result == TEMPS[PERIOD_REDUCED]


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


def test_all_days_set():
    """ALL_DAYS contains exactly the 7 canonical day tokens."""
    assert ALL_DAYS == {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

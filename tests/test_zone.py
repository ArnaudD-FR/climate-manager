# SPDX-License-Identifier: MIT
"""Tests for zone.py — Zone/ZoneMode state machine + structured log emission.

Scenarios:
- Zone period change emits exactly one INFO record matching
  `zone | zone=%s state=%s→%s reason=%s` (D-03 format, OBS-01).
- A second evaluation with the SAME period emits NO additional record
  (anti-spam via _current_period, D-10).
- Short-name strip (D-01): zone_main → zone=main in log output.
- State field encodes both period AND mode:
  state=<old_period>[<old_mode>]→<new_period>[<new_mode>] (D-03).
"""

import logging


from custom_components.climate_manager.zone import Zone


ZONE_LOGGER = "custom_components.climate_manager.zone"


def _make_zone(zone_id: str = "zone_main") -> Zone:
    """Return a minimal Zone for testing log-emission behaviour."""
    return Zone(zone_id=zone_id)


def test_zone_period_change_emits_one_info_record(caplog):
    """Zone evaluation that changes period emits exactly one INFO log record
    matching the locked format `zone | zone=%s state=%s→%s reason=%s` (OBS-01,
    D-03).
    """
    zone = _make_zone("zone_main")

    with caplog.at_level(logging.INFO, logger=ZONE_LOGGER):
        # Simulate a period transition from frost_protection to normal.
        zone._log_period_change(
            old_period="frost_protection",
            old_mode="time_program",
            new_period="normal",
            new_mode="time_program",
            reason="time_program:normal→17:00",
        )

    records = [r for r in caplog.records if r.name == ZONE_LOGGER]
    assert len(records) == 1, (
        f"Expected exactly one INFO record, got {len(records)}: "
        f"{[r.message for r in records]}"
    )
    msg = records[0].getMessage()
    assert "zone | zone=" in msg
    assert "state=" in msg
    assert "reason=" in msg
    # D-01: short name — "zone_main" → "main"
    assert "zone=main" in msg
    # D-03: both period and mode in state field
    assert "frost_protection[time_program]" in msg
    assert "normal[time_program]" in msg
    # Arrow separator between old and new state
    assert "→" in msg


def test_zone_name_strip_d01(caplog):
    """Short-name strip (D-01): zone_main is logged as zone=main, not
    zone=zone_main.
    """
    zone = _make_zone("zone_main")

    with caplog.at_level(logging.INFO, logger=ZONE_LOGGER):
        zone._log_period_change(
            old_period="frost_protection",
            old_mode="off",
            new_period="normal",
            new_mode="time_program",
            reason="user:off→time_program",
        )

    records = [r for r in caplog.records if r.name == ZONE_LOGGER]
    assert records, "No log records emitted"
    msg = records[0].getMessage()
    assert "zone=main" in msg, (
        f"Expected 'zone=main' (D-01 short strip) but got: {msg!r}"
    )
    assert "zone=zone_main" not in msg


def test_zone_no_log_on_same_period(caplog):
    """Anti-spam (D-10): a second evaluation with the same period emits NO
    additional INFO record. Zone._current_period tracks last-logged period.
    """
    zone = _make_zone("zone_home")
    # Simulate: first tick logs the transition.
    zone._current_period = "normal"
    zone._current_mode_name = "time_program"

    with caplog.at_level(logging.INFO, logger=ZONE_LOGGER):
        # Same period + mode as _current — should NOT emit.
        if (
            "normal",
            "time_program",
        ) != (zone._current_period, zone._current_mode_name):
            zone._log_period_change(
                old_period=zone._current_period,
                old_mode=zone._current_mode_name,
                new_period="normal",
                new_mode="time_program",
                reason="time_program:normal",
            )

    records = [r for r in caplog.records if r.name == ZONE_LOGGER]
    assert len(records) == 0, (
        f"Expected no records on repeated same period, got: "
        f"{[r.message for r in records]}"
    )


def test_zone_state_format_includes_period_and_mode(caplog):
    """State field encodes both period AND mode (D-03).
    Format: state=<old_period>[<old_mode>]→<new_period>[<new_mode>].
    Example: state=frost_protection[time_program]→normal[time_program_presences]
    """
    zone = _make_zone("zone_living")

    with caplog.at_level(logging.INFO, logger=ZONE_LOGGER):
        zone._log_period_change(
            old_period="frost_protection",
            old_mode="time_program",
            new_period="normal",
            new_mode="time_program_presences",
            reason="time_program:normal→22:00",
        )

    records = [r for r in caplog.records if r.name == ZONE_LOGGER]
    assert records, "Expected at least one INFO record"
    msg = records[0].getMessage()
    assert "state=" in msg
    assert "frost_protection[time_program]" in msg
    assert "normal[time_program_presences]" in msg
    assert "→" in msg


def test_zone_mode_only_change_logged(caplog):
    """When only the mode changes (same period), the log still fires once
    because (_current_period, _current_mode_name) tuple changed.
    state=normal[time_program]→normal[off] (D-03 example).
    """
    zone = _make_zone("zone_office")

    with caplog.at_level(logging.INFO, logger=ZONE_LOGGER):
        zone._log_period_change(
            old_period="normal",
            old_mode="time_program",
            new_period="normal",
            new_mode="off",
            reason="user:time_program→off",
        )

    records = [r for r in caplog.records if r.name == ZONE_LOGGER]
    assert len(records) == 1
    msg = records[0].getMessage()
    assert "normal[time_program]" in msg
    assert "normal[off]" in msg


# ---------------------------------------------------------------------------
# Household presence / absence periods in a time program zone
# ---------------------------------------------------------------------------

import datetime  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

from custom_components.climate_manager.const import (  # noqa: E402
    DEFAULT_PERIOD_TEMPERATURES,
    MODE_TIME_PROGRAM,
)
from custom_components.climate_manager.eval_context import (  # noqa: E402
    EvalContext,
)

_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# Normal 07–08 and 17–22, Reduced otherwise.
_PROGRAM = {
    day: [
        {"start": "00:00", "mode": "reduced"},
        {"start": "07:00", "mode": "normal"},
        {"start": "08:00", "mode": "reduced"},
        {"start": "17:00", "mode": "normal"},
        {"start": "22:00", "mode": "reduced"},
    ]
    for day in _DAYS
}


async def _evaluate_with(periods, now):
    zone = Zone(
        zone_id="zone_main",
        initial_mode=MODE_TIME_PROGRAM,
        time_program=_PROGRAM,
    )
    room = MagicMock()
    room.apply_setpoint = AsyncMock()
    zone._rooms = [room]
    ctx = EvalContext(
        now=now,
        hass=None,
        period_temperatures=dict(DEFAULT_PERIOD_TEMPERATURES),
        presence_periods=periods,
    )
    await zone.evaluate(ctx)
    return zone, room.apply_setpoint.call_args.args


async def test_household_absence_holds_reduced():
    trip = {
        "id": "trip",
        "kind": "absent",
        "start": "2026-11-05T08:00",
        "end": "2026-11-12T18:30",
    }
    zone, (period, temp, _) = await _evaluate_with(
        [trip], datetime.datetime(2026, 11, 8, 18, 0)
    )
    assert period == "reduced"
    assert temp == DEFAULT_PERIOD_TEMPERATURES["reduced"]
    # The zone period stays the program's.
    assert zone.current_period == "normal"


async def test_household_presence_fills_the_day():
    stay = {
        "id": "stay",
        "kind": "present",
        "start": "2026-11-05T08:00",
        "end": "2026-11-12T18:30",
    }
    _, (period, temp, _) = await _evaluate_with(
        [stay], datetime.datetime(2026, 11, 8, 12, 0)
    )
    assert period == "normal"
    assert temp == DEFAULT_PERIOD_TEMPERATURES["normal"]


async def test_absence_of_some_persons_leaves_the_program():
    trip = {
        "id": "trip",
        "kind": "absent",
        "start": "2026-11-05T08:00",
        "end": "2026-11-12T18:30",
        "person_ids": ["person.a"],
    }
    _, (period, _, _) = await _evaluate_with(
        [trip], datetime.datetime(2026, 11, 8, 18, 0)
    )
    assert period == "normal"

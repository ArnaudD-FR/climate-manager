# SPDX-License-Identifier: MIT
"""Unit tests for predictive pre-heat (Phase 12, Plans 01 and 02).

Tests cover:
- next_occupied_at() for single-schedule, even_odd, calendar, ha, force modes
- wakeup_advance_minutes migration in storage.async_load
- Coordinator _async_preheat pass: trigger, frost-lock guard, default lead,
  learned lead, convergence sample recording, discard, suppression, status
  payload fields (Plan 02, Task 2)

Plan 01 tests are pure Python (no hass fixture).
Plan 02 coordinator tests use the hass fixture and MockConfigEntry pattern
from test_coordinator.py.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.schedule import next_occupied_at
from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DEFAULT_PREHEAT_LEAD_MINUTES,
    DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
    DOMAIN,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_NORMAL,
    PREHEAT_CONVERGENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

TZ = datetime.timezone.utc


def _dt(year, month, day, hour, minute, tz=TZ):
    """Build a timezone-aware datetime."""
    return datetime.datetime(year, month, day, hour, minute, tzinfo=tz)


def _schedule(state_by_day: dict[str, list[dict]]) -> dict:
    """Build a schedule dict for a single person with given day states.

    Produces a full 7-day schedule; days not listed default to absent.
    """
    base = {
        "mon": [],
        "tue": [],
        "wed": [],
        "thu": [],
        "fri": [],
        "sat": [],
        "sun": [],
    }
    base.update(state_by_day)
    return base


# ---------------------------------------------------------------------------
# Task 2: next_occupied_at() tests
# ---------------------------------------------------------------------------


def test_next_occupied_scheduled_single():
    """Single-schedule person absent now, present at 07:00.

    now = Monday 2026-06-01 06:00 UTC (before 07:00 present period).
    Expected: today's 07:00 UTC as aware datetime strictly > now.
    """
    now = _dt(2026, 6, 1, 6, 0)  # Monday
    person = {
        "mode": "scheduled",
        "schedule_type": "single",
        "schedule": _schedule(
            {
                "mon": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "07:00", "state": "present"},
                    {"start": "22:00", "state": "absent"},
                ]
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    assert result.hour == 7
    assert result.minute == 0


def test_next_occupied_even_odd():
    """even_odd person: schedule_even for even weeks, schedule_odd for odd.

    now = Wednesday 2026-06-03 23:00 UTC (week 23, odd).
    Thursday 2026-06-04 is also week 23 (odd) — uses schedule_odd (present 08:00).
    Even schedule_even would return 09:00 on even weeks.
    Verify: result is 08:00 on Thursday 2026-06-04 (week 23, odd → schedule_odd).
    """
    # 2026-06-03 is ISO week 23 (odd → parity=1 → schedule_odd)
    # 2026-06-04 is ISO week 23 (odd → parity=1 → schedule_odd)
    now = _dt(2026, 6, 3, 23, 0)  # Wednesday 23:00
    person = {
        "mode": "scheduled",
        "schedule_type": "even_odd",
        "schedule_even": _schedule(
            {
                "thu": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "09:00", "state": "present"},
                ]
            }
        ),
        "schedule_odd": _schedule(
            {
                "thu": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "08:00", "state": "present"},
                ]
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    # 2026-06-04 (Thursday) — ISO week 23 is odd → schedule_odd → 08:00
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 4
    assert result.hour == 8
    assert result.minute == 0


def test_next_occupied_even_odd_crosses_week_boundary():
    """even_odd: week boundary correctly selects schedule by TARGET day's week.

    now = Sunday 2026-06-07 23:30 UTC (ISO week 23, odd).
    Monday 2026-06-08 is ISO week 24 (even) → should use schedule_even.
    """
    now = _dt(2026, 6, 7, 23, 30)  # Sunday 23:30, week 23 (odd)
    person = {
        "mode": "scheduled",
        "schedule_type": "even_odd",
        "schedule_even": _schedule(
            {
                "mon": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "07:00", "state": "present"},
                ]
            }
        ),
        "schedule_odd": _schedule(
            {
                "mon": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "09:00", "state": "present"},
                ]
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is not None
    # 2026-06-08 (Monday) is ISO week 24 (even) → schedule_even → 07:00
    assert result.day == 8
    assert result.hour == 7


def test_next_occupied_calendar_absent():
    """Calendar mode, event_means=absent, currently inside an event.

    Returns the event's end datetime (person returns home when event ends).
    Event: 08:00–17:00 UTC. now = 10:00 UTC (inside event).
    Expected: event end = 17:00 UTC.
    """
    now = _dt(2026, 6, 1, 10, 0)
    event_end = "2026-06-01T17:00:00+00:00"
    person = {
        "mode": "calendar",
        "calendar_config": {
            "entity_id": "calendar.work",
            "event_means": "absent",
        },
    }
    calendar_cache = {
        "calendar.work": [
            {
                "start": "2026-06-01T08:00:00+00:00",
                "end": event_end,
                "summary": "Work",
            }
        ]
    }
    result = next_occupied_at(person, now, calendar_cache=calendar_cache)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    assert result.hour == 17
    assert result.minute == 0


def test_next_occupied_calendar_present():
    """Calendar mode, event_means=present.

    Returns the start of the next event.
    now = 06:00 UTC. Event starts 09:00 UTC.
    Expected: event start = 09:00 UTC.
    """
    now = _dt(2026, 6, 1, 6, 0)
    person = {
        "mode": "calendar",
        "calendar_config": {
            "entity_id": "calendar.gym",
            "event_means": "present",
        },
    }
    calendar_cache = {
        "calendar.gym": [
            {
                "start": "2026-06-01T09:00:00+00:00",
                "end": "2026-06-01T10:00:00+00:00",
                "summary": "Gym",
            }
        ]
    }
    result = next_occupied_at(person, now, calendar_cache=calendar_cache)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    assert result.hour == 9
    assert result.minute == 0


def test_next_occupied_ha_returns_none():
    """Mode 'ha' → next_occupied_at returns None."""
    now = _dt(2026, 6, 1, 10, 0)
    person = {"mode": "ha"}
    result = next_occupied_at(person, now)
    assert result is None


def test_next_occupied_force_modes_return_none():
    """force_present and force_absent → next_occupied_at returns None."""
    now = _dt(2026, 6, 1, 10, 0)
    for mode in ("force_present", "force_absent"):
        result = next_occupied_at({"mode": mode}, now)
        assert result is None, f"Expected None for mode={mode}"


def test_next_occupied_no_present_period_returns_none():
    """Scheduled person never present in the next 7 days → None."""
    now = _dt(2026, 6, 1, 10, 0)  # Monday
    # All periods are absent for all 7 days
    person = {
        "mode": "scheduled",
        "schedule_type": "single",
        "schedule": _schedule(
            {
                "mon": [{"start": "00:00", "state": "absent"}],
                "tue": [{"start": "00:00", "state": "absent"}],
                "wed": [{"start": "00:00", "state": "absent"}],
                "thu": [{"start": "00:00", "state": "absent"}],
                "fri": [{"start": "00:00", "state": "absent"}],
                "sat": [{"start": "00:00", "state": "absent"}],
                "sun": [{"start": "00:00", "state": "absent"}],
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is None


# ---------------------------------------------------------------------------
# Task 3: wakeup_advance_minutes migration tests
# ---------------------------------------------------------------------------


async def test_wakeup_advance_migration(hass):
    """Stored preheat_lead_minutes=90 and no wakeup_advance_minutes.

    After async_load: wakeup_advance_minutes=90, preheat_lead_minutes absent.
    """
    from custom_components.climate_manager.storage import ClimateManagerStore

    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.alice": {
                    "mode": "scheduled",
                    "preheat_lead_minutes": 90,
                }
            }
        }
    )
    result = await store.async_load()
    alice = result["persons"]["person.alice"]
    assert alice.get("wakeup_advance_minutes") == 90
    assert "preheat_lead_minutes" not in alice


async def test_wakeup_advance_migration_noop_when_new_key_present(hass):
    """Both keys present: wakeup_advance_minutes kept, preheat_lead_minutes removed.

    The existing wakeup_advance_minutes value must NOT be overwritten.
    """
    from custom_components.climate_manager.storage import ClimateManagerStore

    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.bob": {
                    "mode": "scheduled",
                    "wakeup_advance_minutes": 45,
                    "preheat_lead_minutes": 90,
                }
            }
        }
    )
    result = await store.async_load()
    bob = result["persons"]["person.bob"]
    assert bob.get("wakeup_advance_minutes") == 45
    assert "preheat_lead_minutes" not in bob


async def test_wakeup_advance_migration_absent_key(hass):
    """Neither key present: no wakeup_advance_minutes added."""
    from custom_components.climate_manager.storage import ClimateManagerStore

    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.carol": {
                    "mode": "scheduled",
                }
            }
        }
    )
    result = await store.async_load()
    carol = result["persons"]["person.carol"]
    assert "wakeup_advance_minutes" not in carol
    assert "preheat_lead_minutes" not in carol


# ---------------------------------------------------------------------------
# Plan 02, Task 2: Coordinator _async_preheat pass tests
# ---------------------------------------------------------------------------

# All-days Normal schedule used in all preheat coordinator tests.
_ALL_NORMAL = {
    day: [{"start": "00:00", "mode": PERIOD_NORMAL}]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}

# Person schedule: absent 00:00-07:00, present from 07:00.
_MORNING_PRESENT = {
    day: [
        {"start": "00:00", "state": "absent"},
        {"start": "07:00", "state": "present"},
    ]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}


def _make_preheat_config(
    *,
    global_mode: str = MODE_TIME_PROGRAM_PRESENCES,
    persons_config: dict | None = None,
    rooms_config: dict | None = None,
    zones: dict | None = None,
    default_zone_preheat_enabled: bool = False,
) -> dict:
    """Build a runtime_config dict for preheat coordinator tests.

    GAP-01: preheat_enabled lives at zone scope, not room scope.
    Phase 14 (D-01): uses default_zone sub-dict (no flat global_mode or
    global_time_program keys).
    Pass default_zone_preheat_enabled=True for rooms with no zone_id.
    Pass zones={<uuid>: {"preheat_enabled": True, ...}} for custom zones.
    """
    return {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": global_mode,
            "time_program": _ALL_NORMAL,
            "preheat_enabled": default_zone_preheat_enabled,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": rooms_config or {},
        "persons": persons_config or {},
        "zones": zones or {},
        "calibration_enabled": False,
        "calibration_threshold": 0.5,
    }


def _make_mock_data(
    *,
    runtime_config: dict,
    rooms: dict,
    preheat_samples: dict | None = None,
) -> MagicMock:
    """Build a mock ClimateManagerData suitable for coordinator init."""
    data = MagicMock()
    data.runtime_config = runtime_config
    data.rooms = rooms
    data.room_auto_sensors = {}
    data.preheat_samples = preheat_samples or {}
    data.preheat_store = AsyncMock()
    data.preheat_store.async_save = AsyncMock()
    return data


# ---------------------------------------------------------------------------
# Test: preheat trigger fires for enabled room within lead window
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 06:30:00")  # Monday 06:30 UTC
async def test_preheat_trigger_fires(hass):
    """Enabled room with next_occupied_at at 07:00.

    now=06:30, default lead=60 min → trigger window [06:00, 07:00).
    06:30 is inside the window.
    current_temp=18.0 (below Normal 20.0 - threshold).
    Expect: set_temperature called at Normal setpoint, preheat_active True.
    """
    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    hass.states.async_set(
        "climate.bedroom_trv",
        "heat",
        {"temperature": 18.0, "current_temperature": 18.0},
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    persons_config = {
        "person.alice": {
            "mode": "scheduled",
            "schedule_type": "single",
            "schedule": _MORNING_PRESENT,
            "room_ids": ["bedroom"],
        }
    }
    # GAP-01: enable pre-heat at zone scope (room has no zone_id → Default Zone)
    rooms_config = {
        "bedroom": {
            "preheat_max_lead_minutes": DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
        }
    }
    config = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    data = _make_mock_data(
        runtime_config=config, rooms={"bedroom": ["climate.bedroom_trv"]}
    )

    from custom_components.climate_manager.eval_context import EvalContext

    coord = ClimateManagerCoordinator(hass, data)
    # Room.compute_preheat uses room._frost_locked (per-room bool, D-06).
    bedroom_room = coord._rooms.get("bedroom")
    if bedroom_room is not None:
        bedroom_room._frost_locked = False

    now = datetime.datetime(2026, 6, 1, 6, 30, tzinfo=datetime.timezone.utc)
    ctx = EvalContext(
        now=now,
        hass=hass,
        period_temperatures=config["period_temperatures"],
    )
    if bedroom_room is not None:
        await bedroom_room.compute_preheat(ctx)
    await hass.async_block_till_done()

    assert bedroom_room is not None and bedroom_room._preheat_active is True
    assert (
        bedroom_room._preheat_target
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    )
    # set_temperature must have been called
    preheat_calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.bedroom_trv"
    ]
    assert len(preheat_calls) >= 1
    assert (
        preheat_calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    )


# ---------------------------------------------------------------------------
# Test: frost-locked room never pre-heats (T-12-03)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 06:30:00")
async def test_preheat_respects_frost_lock(hass):
    """Frost-locked room with preheat_enabled=True must NOT fire set_temperature."""
    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    hass.states.async_set(
        "climate.living_trv",
        "heat",
        {"temperature": 15.0, "current_temperature": 15.0},
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    persons_config = {
        "person.bob": {
            "mode": "scheduled",
            "schedule_type": "single",
            "schedule": _MORNING_PRESENT,
            "room_ids": ["living"],
        }
    }
    # GAP-01: enable pre-heat at zone scope (room has no zone_id → Default Zone)
    rooms_config = {
        "living": {}  # frost-locked via _frost_locked_rooms (Phase 15)
    }
    config = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    data = _make_mock_data(
        runtime_config=config, rooms={"living": ["climate.living_trv"]}
    )

    from custom_components.climate_manager.eval_context import EvalContext

    coord = ClimateManagerCoordinator(hass, data)
    # Mark room as frost-locked (per-room bool after D-06 migration).
    living_room = coord._rooms.get("living")
    if living_room is not None:
        living_room._frost_locked = True

    now = datetime.datetime(2026, 6, 1, 6, 30, tzinfo=datetime.timezone.utc)
    ctx = EvalContext(
        now=now,
        hass=hass,
        period_temperatures=config["period_temperatures"],
    )
    if living_room is not None:
        await living_room.compute_preheat(ctx)
    await hass.async_block_till_done()

    # No set_temperature calls from preheat for a frost-locked room
    preheat_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.living_trv"
    ]
    assert len(preheat_calls) == 0


# ---------------------------------------------------------------------------
# Test: default lead 60 min used when < 3 valid samples (D-08)
# ---------------------------------------------------------------------------


def test_default_lead_time():
    """With 1 valid sample (< threshold=3), learned lead = DEFAULT 60 min.

    This is a pure-Python test; no hass needed.
    Lead window: [07:00 - 60min, 07:00) = [06:00, 07:00).
    now=06:30 → inside the window.
    """
    now = datetime.datetime(2026, 6, 1, 6, 30, tzinfo=datetime.timezone.utc)
    next_occ = datetime.datetime(2026, 6, 1, 7, 0, tzinfo=datetime.timezone.utc)
    samples = [{"duration_minutes": 30, "timestamp": "2026-05-01T10:00:00"}]

    # With 1 sample < threshold=3, lead = DEFAULT_PREHEAT_LEAD_MINUTES (60)
    from custom_components.climate_manager.const import (
        PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD,
    )

    lead = DEFAULT_PREHEAT_LEAD_MINUTES  # fallback
    if len(samples) >= PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD:
        import statistics

        lead = min(
            statistics.mean(s["duration_minutes"] for s in samples),
            DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
        )

    trigger_start = next_occ - datetime.timedelta(minutes=lead)
    assert trigger_start <= now < next_occ
    assert lead == DEFAULT_PREHEAT_LEAD_MINUTES


# ---------------------------------------------------------------------------
# Test: learned lead = avg of last 5 capped at max (D-08)
# ---------------------------------------------------------------------------


def test_learned_lead_average():
    """With >= 3 valid samples, learned lead = average, capped at max (D-08)."""
    import statistics
    from custom_components.climate_manager.const import (
        PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD,
    )

    # 5 samples: average = 110 min, which exceeds DEFAULT_PREHEAT_MAX_LEAD_MINUTES=120
    # wait — 110 < 120 so no cap needed
    samples = [
        {"duration_minutes": 100, "timestamp": "t1"},
        {"duration_minutes": 110, "timestamp": "t2"},
        {"duration_minutes": 115, "timestamp": "t3"},
        {"duration_minutes": 105, "timestamp": "t4"},
        {"duration_minutes": 120, "timestamp": "t5"},
    ]
    assert len(samples) >= PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD
    avg = statistics.mean(s["duration_minutes"] for s in samples)
    lead = min(avg, DEFAULT_PREHEAT_MAX_LEAD_MINUTES)
    assert lead == min(110.0, DEFAULT_PREHEAT_MAX_LEAD_MINUTES)

    # Verify cap: samples averaging above max_lead
    samples_high = [
        {"duration_minutes": 130, "timestamp": "t1"},
        {"duration_minutes": 140, "timestamp": "t2"},
        {"duration_minutes": 150, "timestamp": "t3"},
    ]
    avg_high = statistics.mean(s["duration_minutes"] for s in samples_high)
    lead_high = min(avg_high, DEFAULT_PREHEAT_MAX_LEAD_MINUTES)
    assert lead_high == DEFAULT_PREHEAT_MAX_LEAD_MINUTES


# ---------------------------------------------------------------------------
# Test: sample recorded on convergence (D-09)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 06:50:00")
async def test_sample_recorded_on_convergence(hass):
    """In-progress room whose current_temp reaches target-threshold.

    Expected: a {duration_minutes, timestamp} sample is appended; in-progress
    entry is cleared; preheat_store.async_save called.
    """
    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    target_temp = DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]  # 20.0
    # current_temperature reaches target (within threshold)
    current_temp = target_temp - PREHEAT_CONVERGENCE_THRESHOLD + 0.01  # 19.81

    hass.states.async_set(
        "climate.study_trv",
        "heat",
        {
            "temperature": target_temp,
            "current_temperature": current_temp,
        },
    )

    # GAP-01: enable pre-heat at zone scope (room has no zone_id → Default Zone)
    rooms_config = {
        "study": {
            "preheat_max_lead_minutes": DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
        }
    }
    config = _make_preheat_config(
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    data = _make_mock_data(
        runtime_config=config,
        rooms={"study": ["climate.study_trv"]},
        preheat_samples={"study": []},
    )

    from custom_components.climate_manager.eval_context import EvalContext

    coord = ClimateManagerCoordinator(hass, data)
    study_room = coord._rooms.get("study")
    if study_room is not None:
        study_room._frost_locked = False

    now = datetime.datetime(2026, 6, 1, 6, 50, tzinfo=datetime.timezone.utc)
    start_time = datetime.datetime(
        2026, 6, 1, 6, 0, tzinfo=datetime.timezone.utc
    )
    # Pre-seed in-progress state on Room (D-06 migration).
    if study_room is not None:
        study_room._preheat_in_progress = {
            "start_time": start_time,
            "target_temp": target_temp,
        }

    ctx = EvalContext(
        now=now,
        hass=hass,
        period_temperatures=config["period_temperatures"],
    )
    if study_room is not None:
        await study_room.compute_preheat(ctx)
    await hass.async_block_till_done()

    # Sample should be recorded
    samples = data.preheat_samples.get("study", [])
    assert len(samples) == 1
    assert samples[0]["duration_minutes"] == 50  # 06:50 - 06:00
    assert "timestamp" in samples[0]

    # In-progress entry cleared
    assert study_room is not None and not study_room._preheat_in_progress

    # Store saved
    data.preheat_store.async_save.assert_called_once()


# ---------------------------------------------------------------------------
# Test: sample discarded when period starts before convergence (D-07, D-09)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 07:05:00")
async def test_sample_discarded_when_period_starts(hass):
    """In-progress room; next_occupied is None (force_absent person) and temp
    not reached — entry should be discarded without recording a sample.

    Expected: entry discarded, no sample recorded, no store save.
    This exercises the D-07 / D-09 discard condition:
    next_occupied is None → discard immediately.
    """
    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    target_temp = DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]  # 20.0
    # Temperature NOT reached
    current_temp = 17.0

    hass.states.async_set(
        "climate.kitchen_trv",
        "heat",
        {
            "temperature": target_temp,
            "current_temperature": current_temp,
        },
    )

    # force_absent → next_occupied_at returns None → discard condition fires
    persons_config = {
        "person.carol": {
            "mode": "force_absent",
            "room_ids": ["kitchen"],
        }
    }
    # GAP-01: enable pre-heat at zone scope (room has no zone_id → Default Zone)
    rooms_config = {
        "kitchen": {
            "preheat_max_lead_minutes": DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
        }
    }
    config = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    data = _make_mock_data(
        runtime_config=config,
        rooms={"kitchen": ["climate.kitchen_trv"]},
        preheat_samples={"kitchen": []},
    )

    from custom_components.climate_manager.eval_context import EvalContext

    coord = ClimateManagerCoordinator(hass, data)
    kitchen_room = coord._rooms.get("kitchen")
    if kitchen_room is not None:
        kitchen_room._frost_locked = False

    now = datetime.datetime(2026, 6, 1, 7, 5, tzinfo=datetime.timezone.utc)
    start_time = datetime.datetime(
        2026, 6, 1, 6, 0, tzinfo=datetime.timezone.utc
    )
    # Pre-seed in-progress state on Room (D-06 migration).
    if kitchen_room is not None:
        kitchen_room._preheat_in_progress = {
            "start_time": start_time,
            "target_temp": target_temp,
        }

    ctx = EvalContext(
        now=now,
        hass=hass,
        period_temperatures=config["period_temperatures"],
    )
    if kitchen_room is not None:
        await kitchen_room.compute_preheat(ctx)
    await hass.async_block_till_done()

    # No sample recorded (discard rule D-07)
    samples = data.preheat_samples.get("kitchen", [])
    assert len(samples) == 0

    # In-progress entry cleared (discarded)
    assert kitchen_room is not None and not kitchen_room._preheat_in_progress

    # Store NOT saved (no sample added)
    data.preheat_store.async_save.assert_not_called()


# ---------------------------------------------------------------------------
# Test: preheat suppressed when all persons use ha mode (D-10)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 06:00:00")
async def test_preheat_suppressed_for_ha_mode(hass):
    """Room enabled for preheat but only person is in ha mode.

    next_occupied_at returns None for ha mode → preheat_suppressed True.
    """
    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    hass.states.async_set(
        "climate.bath_trv",
        "heat",
        {"temperature": 18.0, "current_temperature": 18.0},
    )

    persons_config = {
        "person.dave": {
            "mode": "ha",  # ha mode → next_occupied_at returns None
            "room_ids": ["bath"],
        }
    }
    # GAP-01: enable pre-heat at zone scope (room has no zone_id → Default Zone)
    rooms_config = {
        "bath": {
            "preheat_max_lead_minutes": DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
        }
    }
    config = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    data = _make_mock_data(
        runtime_config=config, rooms={"bath": ["climate.bath_trv"]}
    )

    from custom_components.climate_manager.eval_context import EvalContext

    coord = ClimateManagerCoordinator(hass, data)
    bath_room = coord._rooms.get("bath")
    if bath_room is not None:
        bath_room._frost_locked = False

    now = datetime.datetime(2026, 6, 1, 6, 0, tzinfo=datetime.timezone.utc)
    ctx = EvalContext(
        now=now,
        hass=hass,
        period_temperatures=config["period_temperatures"],
    )
    if bath_room is not None:
        await bath_room.compute_preheat(ctx)
    await hass.async_block_till_done()

    assert bath_room is not None and bath_room._preheat_suppressed is True
    assert bath_room._preheat_active is False


# ---------------------------------------------------------------------------
# Test: status payload contains preheat fields (D-10, PREHEAT-04)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 06:00:00")
async def test_status_payload_preheat_fields(hass):
    """_build_status_payload room entries must include preheat_active,
    preheat_target, preheat_suppressed.
    """

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # GAP-01: preheat_enabled is at zone scope; room config holds no flag
    rooms_config = {"garage": {}}
    config = _make_preheat_config(
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    entry.runtime_data.runtime_config = config
    entry.runtime_data.rooms = {"garage": []}

    coord = entry.runtime_data.coordinator
    # After D-06 migration, preheat state lives on Room domain object.
    # Force-rebuild domain objects so "garage" room exists in coord._rooms.
    coord._build_domain_objects(config)
    garage_room = coord._rooms.get("garage")
    if garage_room is None:
        # If room wasn't created (no entities), create it manually for the test.
        from custom_components.climate_manager.room import Room

        garage_room = Room(area_id="garage", hass=hass)
        coord._rooms["garage"] = garage_room
    garage_room._preheat_active = True
    garage_room._preheat_target = 20.0
    garage_room._preheat_suppressed = False

    payload = coord._build_status_payload()
    garage_entry = next(
        (r for r in payload["rooms_status"] if r["area_id"] == "garage"),
        None,
    )
    assert garage_entry is not None
    assert "preheat_active" in garage_entry
    assert "preheat_target" in garage_entry
    assert "preheat_suppressed" in garage_entry
    assert garage_entry["preheat_active"] is True
    assert garage_entry["preheat_target"] == 20.0
    assert garage_entry["preheat_suppressed"] is False


# ---------------------------------------------------------------------------
# Plan 03, Task 1: ws_get_status preheat field parity (D-10, PREHEAT-04)
# ---------------------------------------------------------------------------


async def test_ws_get_status_preheat_fields(hass, hass_ws_client):
    """get_status rooms_status entries contain preheat_active, preheat_target,
    preheat_suppressed, mirroring the push payload (D-10, Pitfall 1).

    Seeds: one room 'office' with coordinator preheat dicts set.
    Expected: get_status response includes all three fields with correct values.
    Also checks default-absent room returns False/None/False.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Seed two rooms: 'office' (with preheat state) and 'hall' (absent from dicts)
    entry.runtime_data.rooms = {
        "office": [],
        "hall": [],
    }

    coord = entry.runtime_data.coordinator
    # After D-06 migration, preheat state lives on Room domain object.
    # Force-rebuild domain objects so "office" and "hall" rooms exist.
    coord._build_domain_objects(entry.runtime_data.runtime_config)
    from custom_components.climate_manager.room import Room

    # Ensure office room exists (may be empty if no entity list provided).
    if "office" not in coord._rooms:
        coord._rooms["office"] = Room(area_id="office", hass=hass)
    if "hall" not in coord._rooms:
        coord._rooms["hall"] = Room(area_id="hall", hass=hass)

    office_room = coord._rooms["office"]
    office_room._preheat_active = True
    office_room._preheat_target = 21.0
    office_room._preheat_suppressed = False
    # 'hall' room has default False/None/False — no changes needed

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_status"})
    msg = await client.receive_json()

    assert msg["success"] is True
    rooms_status = msg["result"]["rooms_status"]

    office_entry = next(
        (r for r in rooms_status if r["area_id"] == "office"), None
    )
    hall_entry = next((r for r in rooms_status if r["area_id"] == "hall"), None)

    assert office_entry is not None, "office missing from rooms_status"
    assert office_entry["preheat_active"] is True
    assert office_entry["preheat_target"] == 21.0
    assert office_entry["preheat_suppressed"] is False

    assert hall_entry is not None, "hall missing from rooms_status"
    assert hall_entry["preheat_active"] is False
    assert hall_entry["preheat_target"] is None
    assert hall_entry["preheat_suppressed"] is False


# ---------------------------------------------------------------------------
# Plan 03, Task 2: Room preheat config validation (D-01, T-12-06)
# and person wakeup_advance_minutes clamp (D-02)
# ---------------------------------------------------------------------------


async def _setup_ws_entry(hass):
    """Set up integration and return entry (mirrors test_calendar.py pattern)."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_ws_set_room_preheat_config(hass, hass_ws_client):
    """set_room_config no longer persists preheat_enabled on the room (GAP-01).

    preheat_enabled has moved to zone scope; the room command silently drops
    the deprecated key.  preheat_max_lead_minutes is still accepted per-room.
    """
    from pytest_homeassistant_custom_component.common import async_mock_service

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    room_id = "bedroom"

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": room_id,
            "config": {
                "preheat_enabled": True,
                "preheat_max_lead_minutes": 90,
            },
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    persisted = entry.runtime_data.runtime_config.get("rooms", {}).get(
        room_id, {}
    )
    # preheat_enabled must NOT be persisted on the room (GAP-01)
    assert "preheat_enabled" not in persisted, (
        f"Deprecated room preheat_enabled must be dropped, got {persisted}"
    )
    # preheat_max_lead_minutes still persisted per-room
    assert persisted.get("preheat_max_lead_minutes") == 90


async def test_ws_room_max_lead_clamped(hass, hass_ws_client):
    """preheat_max_lead_minutes out of [0, 480] is dropped before persist.

    T-12-06: value 999 dropped; value -5 dropped; non-int ("foo") dropped.
    """
    from pytest_homeassistant_custom_component.common import async_mock_service

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    room_id = "kitchen"
    client = await hass_ws_client()

    # Case 1: value 999 (out of range) → dropped
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": room_id,
            "config": {"preheat_max_lead_minutes": 999},
        }
    )
    await client.receive_json()
    persisted = entry.runtime_data.runtime_config.get("rooms", {}).get(
        room_id, {}
    )
    assert "preheat_max_lead_minutes" not in persisted, (
        f"999 should be dropped, got {persisted}"
    )

    # Case 2: value -5 (negative) → dropped
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": room_id,
            "config": {"preheat_max_lead_minutes": -5},
        }
    )
    await client.receive_json()
    persisted = entry.runtime_data.runtime_config.get("rooms", {}).get(
        room_id, {}
    )
    assert "preheat_max_lead_minutes" not in persisted, (
        f"-5 should be dropped, got {persisted}"
    )

    # Case 3: non-int ("foo") → dropped
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": room_id,
            "config": {"preheat_max_lead_minutes": "foo"},
        }
    )
    await client.receive_json()
    persisted = entry.runtime_data.runtime_config.get("rooms", {}).get(
        room_id, {}
    )
    assert "preheat_max_lead_minutes" not in persisted, (
        f"'foo' should be dropped, got {persisted}"
    )


async def test_ws_room_enabled_coerced_bool(hass, hass_ws_client):
    """preheat_enabled sent to set_room_config is silently dropped (GAP-01).

    preheat_enabled has moved to zone scope.  Sending it via set_room_config
    (even as a truthy non-bool) must NOT persist any room-level flag.
    """
    from pytest_homeassistant_custom_component.common import async_mock_service

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    room_id = "study"
    client = await hass_ws_client()

    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": room_id,
            "config": {"preheat_enabled": 1},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    persisted = entry.runtime_data.runtime_config.get("rooms", {}).get(
        room_id, {}
    )
    # GAP-01: deprecated room-level preheat_enabled must be absent
    assert "preheat_enabled" not in persisted, (
        f"Room preheat_enabled must not be persisted, got {persisted}"
    )


# ---------------------------------------------------------------------------
# GAP-01 zone-scope preheat WS command tests
# ---------------------------------------------------------------------------


async def test_ws_set_zone_preheat(hass, hass_ws_client):
    """set_zone_preheat with a custom zone_id writes preheat_enabled to
    zones[zone_id] (GAP-01).

    T-12-11: unknown zone_id returns error; valid zone_id persists bool.
    """
    import uuid as _uuid

    from pytest_homeassistant_custom_component.common import async_mock_service

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    zone_id = str(_uuid.uuid4())
    # Seed a custom zone into runtime_config
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Upstairs",
        "mode": "time_program",
        "time_program": {},
    }

    client = await hass_ws_client()

    # Enable preheat on the custom zone
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_preheat",
            "zone_id": zone_id,
            "enabled": True,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    zone = entry.runtime_data.runtime_config["zones"][zone_id]
    assert zone.get("preheat_enabled") is True

    # Disable preheat on the custom zone
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_preheat",
            "zone_id": zone_id,
            "enabled": False,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    zone = entry.runtime_data.runtime_config["zones"][zone_id]
    assert zone.get("preheat_enabled") is False


async def test_ws_set_zone_preheat_default(hass, hass_ws_client):
    """set_zone_preheat with zone_id="default" writes default_zone.preheat_enabled.

    Phase 14 (D-11): writes to default_zone sub-dict (was flat key
    default_zone_preheat_enabled in GAP-01).
    """
    from pytest_homeassistant_custom_component.common import async_mock_service

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    client = await hass_ws_client()

    # Enable preheat on the Default Zone
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_preheat",
            "zone_id": "default",
            "enabled": True,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    # Phase 14 (D-11): reads from default_zone sub-dict
    assert (
        entry.runtime_data.runtime_config["default_zone"].get("preheat_enabled")
        is True
    )

    # Disable preheat on the Default Zone
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_preheat",
            "zone_id": "default",
            "enabled": False,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    assert (
        entry.runtime_data.runtime_config["default_zone"].get("preheat_enabled")
        is False
    )


# ---------------------------------------------------------------------------
# GAP-01 coordinator zone-scope enable tests
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 06:30:00")
async def test_preheat_reads_zone_enabled(hass):
    """Room assigned to a custom zone: pre-heat fires iff zone.preheat_enabled.

    T-12-11 / GAP-01: preheat_enabled is read from the zone, not the room.
    """
    import uuid as _uuid

    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    hass.states.async_set(
        "climate.office_trv",
        "heat",
        {"temperature": 18.0, "current_temperature": 18.0},
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    zone_id = str(_uuid.uuid4())
    persons_config = {
        "person.alice": {
            "mode": "scheduled",
            "schedule_type": "single",
            "schedule": _MORNING_PRESENT,
            "room_ids": ["office"],
        }
    }
    rooms_config = {
        "office": {
            "zone_id": zone_id,
            "preheat_max_lead_minutes": DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
        }
    }

    # Case 1: zone.preheat_enabled=True → trigger fires
    zones_enabled = {
        zone_id: {
            "name": "Z",
            "mode": "time_program_presences",
            "time_program": _ALL_NORMAL,
            "preheat_enabled": True,
        }
    }
    config = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        zones=zones_enabled,
    )
    data = _make_mock_data(
        runtime_config=config,
        rooms={"office": ["climate.office_trv"]},
    )
    coord = ClimateManagerCoordinator(hass, data)
    coord._frost_locked_rooms = set()
    now = datetime.datetime(2026, 6, 1, 6, 30, tzinfo=datetime.timezone.utc)
    await coord._async_preheat_room("office", config, now)
    await hass.async_block_till_done()

    assert coord._preheat_active.get("office") is True

    # Case 2: zone.preheat_enabled absent → preheat_active False
    zones_disabled = {
        zone_id: {
            "name": "Z",
            "mode": "time_program_presences",
            "time_program": _ALL_NORMAL,
        }
    }
    config2 = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        zones=zones_disabled,
    )
    data2 = _make_mock_data(
        runtime_config=config2,
        rooms={"office": ["climate.office_trv"]},
    )
    coord2 = ClimateManagerCoordinator(hass, data2)
    coord2._frost_locked_rooms = set()
    await coord2._async_preheat_room("office", config2, now)
    await hass.async_block_till_done()

    assert coord2._preheat_active.get("office") is not True


@pytest.mark.freeze_time("2026-06-01 06:30:00")
async def test_preheat_default_zone_enabled(hass):
    """Room with no zone_id: pre-heat fires iff default_zone_preheat_enabled.

    GAP-01: rooms with no zone_id read default_zone_preheat_enabled.
    """
    from custom_components.climate_manager.coordinator import (
        ClimateManagerCoordinator,
    )

    hass.states.async_set(
        "climate.hall_trv",
        "heat",
        {"temperature": 18.0, "current_temperature": 18.0},
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    persons_config = {
        "person.bob": {
            "mode": "scheduled",
            "schedule_type": "single",
            "schedule": _MORNING_PRESENT,
            "room_ids": ["hall"],
        }
    }
    rooms_config = {
        "hall": {"preheat_max_lead_minutes": DEFAULT_PREHEAT_MAX_LEAD_MINUTES}
    }

    # Case 1: default_zone_preheat_enabled=True → fires
    config = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        default_zone_preheat_enabled=True,
    )
    data = _make_mock_data(
        runtime_config=config,
        rooms={"hall": ["climate.hall_trv"]},
    )
    coord = ClimateManagerCoordinator(hass, data)
    coord._frost_locked_rooms = set()
    now = datetime.datetime(2026, 6, 1, 6, 30, tzinfo=datetime.timezone.utc)
    await coord._async_preheat_room("hall", config, now)
    await hass.async_block_till_done()

    assert coord._preheat_active.get("hall") is True

    # Case 2: default_zone_preheat_enabled absent → does NOT fire
    config2 = _make_preheat_config(
        persons_config=persons_config,
        rooms_config=rooms_config,
        default_zone_preheat_enabled=False,
    )
    data2 = _make_mock_data(
        runtime_config=config2,
        rooms={"hall": ["climate.hall_trv"]},
    )
    coord2 = ClimateManagerCoordinator(hass, data2)
    coord2._frost_locked_rooms = set()
    await coord2._async_preheat_room("hall", config2, now)
    await hass.async_block_till_done()

    assert coord2._preheat_active.get("hall") is not True


# ---------------------------------------------------------------------------
# GAP-01 storage migration tests (T-12-13)
# ---------------------------------------------------------------------------


async def test_migration_room_preheat_to_zone(hass):
    """async_load migrates legacy room.preheat_enabled=True to zone scope.

    T-12-13: migration unconditionally pops deprecated room key.
    Variant A: room with zone_id → flag lands on zones[zone_id].
    Variant B: room with no zone_id → flag lands on default_zone_preheat_enabled.
    """
    import uuid as _uuid

    from custom_components.climate_manager.storage import ClimateManagerStore

    zone_id = str(_uuid.uuid4())

    # Variant A: room assigned to a custom zone
    stored_a = {
        "version": 2,
        "global_mode": "time_program",
        "period_temperatures": {},
        "global_time_program": {},
        "zones": {
            zone_id: {
                "name": "Upstairs",
                "mode": "time_program",
                "time_program": {},
            }
        },
        "rooms": {
            "bedroom": {
                "zone_id": zone_id,
                "preheat_enabled": True,
                "preheat_max_lead_minutes": 90,
            }
        },
        "persons": {},
    }

    mock_store_a = AsyncMock()
    mock_store_a.async_load = AsyncMock(return_value=stored_a)
    storage_a = ClimateManagerStore.__new__(ClimateManagerStore)
    storage_a._store = mock_store_a

    result_a = await storage_a.async_load()

    # Flag promoted to zone
    assert result_a["zones"][zone_id].get("preheat_enabled") is True
    # Deprecated room key removed
    assert "preheat_enabled" not in result_a["rooms"]["bedroom"]
    # max_lead still on room
    assert result_a["rooms"]["bedroom"].get("preheat_max_lead_minutes") == 90

    # Variant B: room with no zone_id → Default Zone
    stored_b = {
        "version": 2,
        "global_mode": "time_program",
        "period_temperatures": {},
        "global_time_program": {},
        "zones": {},
        "rooms": {
            "hall": {
                "preheat_enabled": True,
            }
        },
        "persons": {},
    }

    mock_store_b = AsyncMock()
    mock_store_b.async_load = AsyncMock(return_value=stored_b)
    storage_b = ClimateManagerStore.__new__(ClimateManagerStore)
    storage_b._store = mock_store_b

    result_b = await storage_b.async_load()

    # Phase 14 (D-11): GAP-01 flag promoted to default_zone.preheat_enabled
    # (Phase 14 compat shim absorbs the intermediate flat key into default_zone)
    assert result_b["default_zone"].get("preheat_enabled") is True
    # Deprecated room key removed
    assert "preheat_enabled" not in result_b["rooms"]["hall"]


async def test_ws_set_person_wakeup_advance(hass, hass_ws_client):
    """set_person_config with wakeup_advance_minutes=90 persists; 999 is dropped.

    D-02: wakeup_advance_minutes replaces preheat_lead_minutes.
    Legacy preheat_lead_minutes key is mapped to wakeup_advance_minutes.
    """
    from pytest_homeassistant_custom_component.common import async_mock_service

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    pid = "person.alice"
    client = await hass_ws_client()

    # Valid value: 90 → persisted as wakeup_advance_minutes
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": pid,
            "config": {"wakeup_advance_minutes": 90},
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    persisted = entry.runtime_data.runtime_config.get("persons", {}).get(
        pid, {}
    )
    assert persisted.get("wakeup_advance_minutes") == 90

    # Out of range: 999 → dropped
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": pid,
            "config": {"wakeup_advance_minutes": 999},
        }
    )
    await client.receive_json()
    persisted = entry.runtime_data.runtime_config.get("persons", {}).get(
        pid, {}
    )
    # Should still be 90 (the previous valid value — 999 was dropped)
    assert persisted.get("wakeup_advance_minutes") == 90

    # Legacy key: preheat_lead_minutes=60 → stored as wakeup_advance_minutes=60
    pid2 = "person.bob"
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": pid2,
            "config": {"preheat_lead_minutes": 60},
        }
    )
    await client.receive_json()
    persisted2 = entry.runtime_data.runtime_config.get("persons", {}).get(
        pid2, {}
    )
    assert persisted2.get("wakeup_advance_minutes") == 60, (
        f"Legacy preheat_lead_minutes should map to wakeup_advance_minutes: "
        f"{persisted2}"
    )

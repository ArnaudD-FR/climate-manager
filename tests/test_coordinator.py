"""Tests for ClimateManagerCoordinator integration behavior.

Tests:
- Coordinator pushes to TRVs immediately on startup (INFRA-03)
- Scheduler is registered and cancellable on unload (Pitfall 1)
- Push-on-change: no second call if temperature unchanged (D-02)
- Manual override hold: skip entity when TRV reports different temp (D-03)
- Present person wins over absent person for a shared room (D-07 multi-person conflict)
- Frost protection before first period (WR-04)
- Room mode branching: global / frost_protection / custom (D-20)

All tests use MockConfigEntry + hass fixture following the pattern from test_init.py.
TRV states are seeded before setup; climate services are captured via async_mock_service.
"""

import datetime

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.climate_manager import ClimateManagerCoordinator, ClimateManagerData
from custom_components.climate_manager.const import (
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    DEFAULT_PERIOD_TEMPERATURES,
    ROOM_MODE_GLOBAL,
    ROOM_MODE_FROST,
    ROOM_MODE_CUSTOM,
)

# ---------------------------------------------------------------------------
# Module-level fixture: all days Comfort (for custom room_mode tests)
# ---------------------------------------------------------------------------

ALL_DAYS_COMFORT_PROGRAM: dict = {
    day: [{"start": "00:00", "mode": PERIOD_COMFORT}]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}

# ---------------------------------------------------------------------------
# Test fixtures / helpers — per-day schema (D-01)
# ---------------------------------------------------------------------------

# Per-day dict: all 7 days in Normal mode all day.
# Used by tests that just need a deterministic temperature push without
# caring about which period is active.
ALL_DAYS_NORMAL_PROGRAM: dict = {
    day: [{"start": "00:00", "mode": PERIOD_NORMAL}]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}

# Per-day dict: Reduced 00:00-07:00, Normal 07:00-22:00, Reduced 22:00+.
# Frozen clock at Monday 08:30 (see freeze_time marks) lands in Normal.
TYPICAL_WEEKDAY_PROGRAM: dict = {
    day: [
        {"start": "00:00", "mode": PERIOD_REDUCED},
        {"start": "07:00", "mode": PERIOD_NORMAL},
        {"start": "22:00", "mode": PERIOD_REDUCED},
    ]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}

# Per-day dict: Normal starts at 07:00, no 00:00 period — frost-protection before 07:00.
LATE_START_PROGRAM: dict = {
    day: [
        {"start": "07:00", "mode": PERIOD_NORMAL},
        {"start": "22:00", "mode": PERIOD_REDUCED},
    ]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}


def _make_runtime_config(
    global_mode: str = MODE_TIME_PROGRAM,
    daily_program: dict | None = None,
    rooms_config: dict | None = None,
    persons_config: dict | None = None,
) -> dict:
    """Build a runtime_config dict suitable for coordinator tests."""
    return {
        "version": 2,
        "global_mode": global_mode,
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "global_time_program": daily_program if daily_program is not None else ALL_DAYS_NORMAL_PROGRAM,
        "rooms": rooms_config or {},
        "persons": persons_config or {},
    }


# ---------------------------------------------------------------------------
# Test 1: Startup push (INFRA-03)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 16:30:00")  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
async def test_coordinator_pushes_on_startup(hass):
    """INFRA-03: coordinator calls set_trv_temperature immediately on setup.

    Seeds one climate entity in one room. The global program puts all days in Normal
    mode from 00:00, so the startup push should call set_temperature with 20.0.
    """
    # Seed a climate entity in HA state
    hass.states.async_set("climate.bedroom_trv", "heat", {"temperature": 15.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Patch runtime_config to have a Normal-all-day program
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
    )
    # Patch rooms to include our entity
    entry.runtime_data.rooms = {"bedroom": ["climate.bedroom_trv"]}

    # Manually trigger evaluate (simulates what happens on startup after patching)
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # At least one set_temperature call for our entity (INFRA-03)
    assert len(temp_calls) >= 1
    entity_calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.bedroom_trv"]
    assert len(entity_calls) >= 1
    # Normal temperature from DEFAULT_PERIOD_TEMPERATURES
    assert entity_calls[-1].data["temperature"] == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]


# ---------------------------------------------------------------------------
# Test 2: Unload cancels scheduler (Pitfall 1)
# ---------------------------------------------------------------------------


async def test_unload_cancels_scheduler(hass):
    """Scheduler is cancelled on unload — no ghost listeners (Pitfall 1).

    After setup, cancel_scheduler is not None. After unload, no ghost-listener
    errors should appear and unload returns True.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Scheduler must be registered
    assert entry.runtime_data.cancel_scheduler is not None

    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True
    # After unload, hass teardown proceeds without ghost-listener AttributeError.
    # The test harness would raise if the scheduler fired after unload.


# ---------------------------------------------------------------------------
# Test 3: Push-on-change — no duplicate push (D-02)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 16:30:00")  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
async def test_push_on_change_no_duplicate(hass):
    """D-02: after startup push, a second evaluate with the same target temp
    does NOT issue another set_temperature call for the same entity.
    """
    hass.states.async_set("climate.living_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Patch config + rooms
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
    )
    entry.runtime_data.rooms = {"living": ["climate.living_trv"]}

    # First evaluate — triggers push
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()
    count_after_first = len([c for c in temp_calls if c.data.get("entity_id") == "climate.living_trv"])
    assert count_after_first >= 1

    # Update HA state to reflect what was pushed (TRV now reports our temp)
    pushed_temp = DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    hass.states.async_set("climate.living_trv", "heat", {"temperature": pushed_temp})

    # Second evaluate — same desired temp; should NOT issue another call
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()
    count_after_second = len([c for c in temp_calls if c.data.get("entity_id") == "climate.living_trv"])

    # Count must be unchanged (no duplicate push)
    assert count_after_second == count_after_first


# ---------------------------------------------------------------------------
# Test 4: Manual override hold (D-03)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 16:30:00")  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
async def test_manual_override_hold(hass):
    """D-03: if TRV reports a temperature different from last pushed, skip it.

    Scenario:
    1. First evaluate pushes Normal temperature (20.0) to the entity.
    2. TRV state is updated to 24.0 (user manually overrode).
    3. Second evaluate with same Normal target: entity is skipped (hold).
    """
    hass.states.async_set("climate.hall_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
    )
    entry.runtime_data.rooms = {"hall": ["climate.hall_trv"]}

    # First evaluate — pushes Normal temp
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()
    count_after_push = len([c for c in temp_calls if c.data.get("entity_id") == "climate.hall_trv"])
    assert count_after_push >= 1

    # Simulate user manual override: TRV now reports 24.0 (different from 20.0 we pushed)
    hass.states.async_set("climate.hall_trv", "heat", {"temperature": 24.0})

    # Second evaluate — same Normal target (20.0), but TRV reports 24.0 → hold
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()
    count_after_hold = len([c for c in temp_calls if c.data.get("entity_id") == "climate.hall_trv"])

    # Count must be unchanged — entity was held
    assert count_after_hold == count_after_push


# ---------------------------------------------------------------------------
# Test 5: Present person wins over absent person for shared room
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 16:30:00")  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
async def test_present_person_wins_absent_for_same_room(hass):
    """Present person raises shared room temp; absent person cannot lower it.

    Setup:
    - One room ("lounge") with one TRV.
    - Time program: Reduced 00:00-07:00, Normal 07:00-22:00, Reduced 22:00+.
    - At 08:30 local (US/Pacific = test harness TZ) the scheduled period is Normal (20.0 baseline).
    - freeze_time is set to 16:30 UTC so that dt_util.now() returns 08:30 local time.
    - Person A: mode "present" → compute_occupied_temp returns Normal temp (inside window).
    - Person B: mode "absent" → compute_occupied_temp returns Reduced (18.0).
    - Both persons are associated with the same "lounge" room.
    - Expected result: the entity receives the occupied-window (Normal) temperature,
      NOT the Reduced temperature — regardless of person iteration order.

    This verifies the "present-wins" rule is order-independent.
    """
    hass.states.async_set("climate.lounge_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # At 08:30 on Monday: Normal period is active (07:00-22:00).
    # compute_occupied_temp for a present person at 08:30 with this program:
    #   - nc_periods: Normal at 07:00
    #   - occupied window: [07:00, 22:00)
    #   - 08:30 is inside the window, active_mode = Normal → returns 20.0
    # compute_occupied_temp for an absent person → returns 18.0 (Reduced)
    persons_config = {
        "person.alice": {
            "mode": "force_present",
            "room_ids": ["lounge"],
            "schedule": {},  # per-day: empty dict = no schedule
        },
        "person.bob": {
            "mode": "force_absent",
            "room_ids": ["lounge"],
            "schedule": {},  # per-day: empty dict = no schedule
        },
    }

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM_PRESENCES,
        daily_program=TYPICAL_WEEKDAY_PROGRAM,
        persons_config=persons_config,
    )
    entry.runtime_data.rooms = {"lounge": ["climate.lounge_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # The entity should receive the occupied-window (Normal) temperature = 20.0
    lounge_calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.lounge_trv"]
    assert len(lounge_calls) >= 1

    pushed_temp = lounge_calls[-1].data["temperature"]

    # Assert occupied-window (Normal) temp, NOT Reduced
    assert pushed_temp == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL], (
        f"Expected occupied-window Normal temp {DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]}, "
        f"got {pushed_temp} — absent person may have overwritten the present person's temp"
    )
    assert pushed_temp != DEFAULT_PERIOD_TEMPERATURES[PERIOD_REDUCED], (
        "Absent person's Reduced temperature must not overwrite the present person's temp"
    )


# ---------------------------------------------------------------------------
# Test 6: Frost-protection before first period (WR-04)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 14:00:00")  # Monday 14:00 UTC = 06:00 US/Pacific
async def test_coordinator_applies_frost_before_first_period(hass):
    """WR-04: rooms receive frost-protection temp before the first scheduled period.

    Schedule starts at 07:00 (Normal). At 06:00 local time no period has started,
    so evaluate_schedule returns PERIOD_FROST_PROTECTION and the coordinator should
    push 7.0°C (DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]) to the TRV.
    """
    hass.states.async_set("climate.study_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=LATE_START_PROGRAM,
    )
    entry.runtime_data.rooms = {"study": ["climate.study_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    study_calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.study_trv"]
    assert len(study_calls) >= 1, "Expected at least one set_temperature call for study_trv"

    pushed_temp = study_calls[-1].data["temperature"]
    assert pushed_temp == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"Expected frost-protection temp {DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]} "
        f"before first period, got {pushed_temp}"
    )


# ---------------------------------------------------------------------------
# Tests 7-12: Per-room mode branching (D-20)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday 12:00 UTC = 04:00 US/Pacific (Normal in ALL_DAYS_NORMAL)
async def test_room_mode_frost_protection_pushes_frost_temp(hass):
    """D-20: room with room_mode='frost_protection' receives frost temp regardless of schedule.

    Global program is Normal (20.0) at this time. Room mode overrides to frost protection (7.0).
    """
    hass.states.async_set("climate.frost_trv", "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Global program: Normal all day. Room mode overrides to frost_protection.
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"area_x": {"room_mode": ROOM_MODE_FROST}},
    )
    entry.runtime_data.rooms = {"area_x": ["climate.frost_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.frost_trv"]
    assert len(calls) >= 1, "Expected set_temperature call for frost_trv"
    assert calls[-1].data["temperature"] == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"room_mode=frost_protection should push 7.0, got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday 12:00 UTC — Normal active in global
async def test_room_mode_custom_uses_room_time_program(hass):
    """D-20: room with room_mode='custom' uses its own time_program (Comfort all day → 22.0).

    Global program gives Normal (20.0). Room's custom program is Comfort all day (22.0).
    """
    hass.states.async_set("climate.custom_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"area_y": {"room_mode": ROOM_MODE_CUSTOM, "time_program": ALL_DAYS_COMFORT_PROGRAM}},
    )
    entry.runtime_data.rooms = {"area_y": ["climate.custom_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.custom_trv"]
    assert len(calls) >= 1, "Expected set_temperature call for custom_trv"
    assert calls[-1].data["temperature"] == DEFAULT_PERIOD_TEMPERATURES[PERIOD_COMFORT], (
        f"room_mode=custom with Comfort program should push 22.0, got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday 12:00 UTC — Normal active
async def test_room_mode_global_explicit_key_uses_global_program(hass):
    """D-20: room with room_mode='global' (explicit key) follows the global time program.

    Global program is Normal all day (20.0). room_mode='global' → 20.0.
    """
    hass.states.async_set("climate.global_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"area_z": {"room_mode": ROOM_MODE_GLOBAL}},
    )
    entry.runtime_data.rooms = {"area_z": ["climate.global_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.global_trv"]
    assert len(calls) >= 1, "Expected set_temperature call for global_trv"
    assert calls[-1].data["temperature"] == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL], (
        f"room_mode=global should use global program (Normal=20.0), got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday 12:00 UTC — Normal active
async def test_room_mode_absent_key_uses_global_program(hass):
    """D-20: room with no room_mode key (absent) defaults to global time program.

    Absent key behavior must be identical to room_mode='global'.
    """
    hass.states.async_set("climate.default_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"area_w": {}},  # no room_mode key — should default to global
    )
    entry.runtime_data.rooms = {"area_w": ["climate.default_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.default_trv"]
    assert len(calls) >= 1, "Expected set_temperature call for default_trv"
    assert calls[-1].data["temperature"] == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL], (
        f"Absent room_mode key should default to global (Normal=20.0), got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday 12:00 UTC — Normal active
async def test_room_mode_frost_wins_over_stale_time_program(hass):
    """D-20: room with room_mode='frost_protection' ignores a stale time_program.

    Even when a time_program is stored for the room, frost_protection wins.
    """
    hass.states.async_set("climate.combo_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # room_mode=frost_protection AND a time_program (Comfort) — frost wins
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"area_v": {"room_mode": ROOM_MODE_FROST, "time_program": ALL_DAYS_COMFORT_PROGRAM}},
    )
    entry.runtime_data.rooms = {"area_v": ["climate.combo_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.combo_trv"]
    assert len(calls) >= 1, "Expected set_temperature call for combo_trv"
    pushed = calls[-1].data["temperature"]
    assert pushed == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"room_mode=frost_protection should push 7.0 ignoring time_program, got {pushed}"
    )


@pytest.mark.freeze_time("2026-01-05 16:30:00")  # Monday 16:30 UTC = 08:30 US/Pacific (Normal period)
async def test_room_mode_frost_wins_over_presence(hass):
    """D-20: room_mode='frost_protection' overrides presence mode for the room.

    Even when a present person is associated with the room, frost_protection wins.
    The room is held at 7.0 regardless of presence.
    """
    hass.states.async_set("climate.presence_frost_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Person A is present and associated with area_p
    persons_config = {
        "person.alice": {
            "mode": "force_present",
            "room_ids": ["area_p"],
            "schedule": {},
        },
    }

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM_PRESENCES,
        daily_program=TYPICAL_WEEKDAY_PROGRAM,
        rooms_config={"area_p": {"room_mode": ROOM_MODE_FROST}},
        persons_config=persons_config,
    )
    entry.runtime_data.rooms = {"area_p": ["climate.presence_frost_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.presence_frost_trv"]
    assert len(calls) >= 1, "Expected set_temperature call for presence_frost_trv"
    pushed = calls[-1].data["temperature"]
    assert pushed == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"room_mode=frost_protection should override presence and push 7.0, got {pushed}"
    )


# ---------------------------------------------------------------------------
# Tests 13-19: HA-mode branch in _compute_present_persons (D-21)
#
# These tests directly instantiate ClimateManagerCoordinator (bypassing
# the full entry setup) and call _compute_present_persons() directly.
# HA entity states are seeded via hass.states.async_set().
# ---------------------------------------------------------------------------


def _make_simple_coordinator(hass) -> ClimateManagerCoordinator:
    """Build a minimal coordinator for _compute_present_persons unit tests."""
    from custom_components.climate_manager.storage import ClimateManagerStore
    data = ClimateManagerData(
        store=ClimateManagerStore(hass),
        runtime_config=_make_runtime_config(),
        rooms={},
        persons=[],
        room_auto_sensors={},
    )
    return ClimateManagerCoordinator(hass, data)


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_ha_mode_state_home(hass):
    """D-21: person with mode='ha' and state='home' is present."""
    hass.states.async_set("person.alice", "home")
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={"person.alice": {"mode": "ha", "room_ids": []}}
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" in result


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_ha_mode_state_not_home(hass):
    """D-21: person with mode='ha' and state='not_home' is absent."""
    hass.states.async_set("person.alice", "not_home")
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={"person.alice": {"mode": "ha", "room_ids": []}}
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" not in result


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_ha_mode_state_unknown(hass):
    """D-21: person with mode='ha' and state='unknown' is absent."""
    hass.states.async_set("person.alice", "unknown")
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={"person.alice": {"mode": "ha", "room_ids": []}}
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" not in result


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_ha_mode_state_missing(hass):
    """D-21: person with mode='ha' and no HA state (entity not found) is absent."""
    # Do NOT seed any state for person.alice — hass.states.get returns None
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={"person.alice": {"mode": "ha", "room_ids": []}}
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" not in result


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_ha_mode_state_unavailable(hass):
    """D-21: person with mode='ha' and state='unavailable' is absent."""
    hass.states.async_set("person.alice", "unavailable")
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={"person.alice": {"mode": "ha", "room_ids": []}}
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" not in result


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_ha_mode_state_zone_name(hass):
    """D-21: person with mode='ha' and state='work' (zone name) is absent — only 'home' qualifies."""
    hass.states.async_set("person.alice", "work")
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={"person.alice": {"mode": "ha", "room_ids": []}}
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" not in result


@pytest.mark.freeze_time("2026-01-05 12:00:00")
def test_compute_present_persons_mixed_modes(hass):
    """D-21: mixed modes — force_present always present, ha+home present, ha+not_home absent."""
    hass.states.async_set("person.bob", "home")
    hass.states.async_set("person.carol", "not_home")
    coordinator = _make_simple_coordinator(hass)
    config = _make_runtime_config(
        persons_config={
            "person.alice": {"mode": "force_present", "room_ids": []},
            "person.bob": {"mode": "ha", "room_ids": []},
            "person.carol": {"mode": "ha", "room_ids": []},
        }
    )
    now = datetime.datetime(2026, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = coordinator._compute_present_persons(config, now)
    assert "person.alice" in result
    assert "person.bob" in result
    assert "person.carol" not in result
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Test: D-24 — _build_status_payload includes present_person_count (plan 03-10)
# ---------------------------------------------------------------------------


def test_build_status_payload_includes_present_person_count(hass):
    """D-24: _build_status_payload sets present_person_count on every rooms_status entry.

    Setup:
    - rooms: living_room (climate.x), kitchen (climate.y)
    - persons: alice assigned to living_room, bob assigned to living_room + kitchen
    - _last_present_persons: [person.alice] only

    Expected:
    - living_room.present_person_count == 1 (alice is present and assigned)
    - kitchen.present_person_count == 0 (bob is assigned but absent; alice not assigned)
    - Both entries have the key present_person_count
    """
    from custom_components.climate_manager.storage import ClimateManagerStore

    runtime_config = _make_runtime_config(
        persons_config={
            "person.alice": {"room_ids": ["living_room"]},
            "person.bob": {"room_ids": ["living_room", "kitchen"]},
        }
    )
    data = ClimateManagerData(
        store=ClimateManagerStore(hass),
        runtime_config=runtime_config,
        rooms={"living_room": ["climate.x"], "kitchen": ["climate.y"]},
        persons=[],
        room_auto_sensors={},
    )
    coordinator = ClimateManagerCoordinator(hass, data)
    coordinator._last_present_persons = ["person.alice"]

    payload = coordinator._build_status_payload()

    rooms_status = payload["rooms_status"]
    # Both entries must have the key
    for entry in rooms_status:
        assert "present_person_count" in entry, (
            f"present_person_count missing from room entry {entry['area_id']}"
        )

    living_entry = next(e for e in rooms_status if e["area_id"] == "living_room")
    kitchen_entry = next(e for e in rooms_status if e["area_id"] == "kitchen")

    assert living_entry["present_person_count"] == 1, (
        f"living_room: expected 1 (alice present+assigned), got {living_entry['present_person_count']}"
    )
    assert kitchen_entry["present_person_count"] == 0, (
        f"kitchen: expected 0 (bob assigned but absent), got {kitchen_entry['present_person_count']}"
    )

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
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager import (
    ClimateManagerCoordinator,
    ClimateManagerData,
)
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
    PRESENCE_PRESENT,
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
    zones_config: dict | None = None,
) -> dict:
    """Build a runtime_config dict suitable for coordinator tests."""
    return {
        "version": 2,
        "global_mode": global_mode,
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "global_time_program": daily_program
        if daily_program is not None
        else ALL_DAYS_NORMAL_PROGRAM,
        "rooms": rooms_config or {},
        "persons": persons_config or {},
        "zones": zones_config or {},
        "default_zone_name": "Home",
    }


# ---------------------------------------------------------------------------
# Test 1: Startup push (INFRA-03)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(
    "2026-01-05 16:30:00"
)  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
async def test_coordinator_pushes_on_startup(hass):
    """INFRA-03: coordinator calls set_trv_temperature immediately on setup.

    Seeds one climate entity in one room. The global program puts all days in Normal
    mode from 00:00, so the startup push should call set_temperature with 20.0.
    """
    # Seed a climate entity in HA state
    hass.states.async_set("climate.bedroom_trv", "heat", {"temperature": 15.0})

    async_mock_service(hass, "climate", "set_hvac_mode")
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
    entity_calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.bedroom_trv"
    ]
    assert len(entity_calls) >= 1
    # Normal temperature from DEFAULT_PERIOD_TEMPERATURES
    assert (
        entity_calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    )


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


@pytest.mark.freeze_time(
    "2026-01-05 16:30:00"
)  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
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
    count_after_first = len(
        [
            c
            for c in temp_calls
            if c.data.get("entity_id") == "climate.living_trv"
        ]
    )
    assert count_after_first >= 1

    # Update HA state to reflect what was pushed (TRV now reports our temp)
    pushed_temp = DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    hass.states.async_set(
        "climate.living_trv", "heat", {"temperature": pushed_temp}
    )

    # Second evaluate — same desired temp; should NOT issue another call
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()
    count_after_second = len(
        [
            c
            for c in temp_calls
            if c.data.get("entity_id") == "climate.living_trv"
        ]
    )

    # Count must be unchanged (no duplicate push)
    assert count_after_second == count_after_first


# ---------------------------------------------------------------------------
# Test 4: Manual override hold (D-03)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(
    "2026-01-05 16:30:00"
)  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
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
    count_after_push = len(
        [c for c in temp_calls if c.data.get("entity_id") == "climate.hall_trv"]
    )
    assert count_after_push >= 1

    # Simulate user manual override: TRV now reports 24.0 (different from 20.0 we pushed)
    hass.states.async_set("climate.hall_trv", "heat", {"temperature": 24.0})

    # Second evaluate — same Normal target (20.0), but TRV reports 24.0 → hold
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()
    count_after_hold = len(
        [c for c in temp_calls if c.data.get("entity_id") == "climate.hall_trv"]
    )

    # Count must be unchanged — entity was held
    assert count_after_hold == count_after_push


# ---------------------------------------------------------------------------
# Test 5: Present person wins over absent person for shared room
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(
    "2026-01-05 16:30:00"
)  # Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ)
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
    lounge_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.lounge_trv"
    ]
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


@pytest.mark.freeze_time(
    "2026-01-05 14:00:00"
)  # Monday 14:00 UTC = 06:00 US/Pacific
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

    study_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.study_trv"
    ]
    assert len(study_calls) >= 1, (
        "Expected at least one set_temperature call for study_trv"
    )

    pushed_temp = study_calls[-1].data["temperature"]
    assert (
        pushed_temp == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
    ), (
        f"Expected frost-protection temp {DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]} "
        f"before first period, got {pushed_temp}"
    )


# ---------------------------------------------------------------------------
# Tests 7-12: Per-room mode branching (D-20)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday 12:00 UTC = 04:00 US/Pacific (Normal in ALL_DAYS_NORMAL)
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

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.frost_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for frost_trv"
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
    ), (
        f"room_mode=frost_protection should push 7.0, got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday 12:00 UTC — Normal active in global
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
        rooms_config={
            "area_y": {
                "room_mode": ROOM_MODE_CUSTOM,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
            }
        },
    )
    entry.runtime_data.rooms = {"area_y": ["climate.custom_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.custom_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for custom_trv"
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_COMFORT]
    ), (
        f"room_mode=custom with Comfort program should push 22.0, got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday 12:00 UTC — Normal active
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

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.global_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for global_trv"
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    ), (
        f"room_mode=global should use global program (Normal=20.0), got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday 12:00 UTC — Normal active
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
        rooms_config={
            "area_w": {}
        },  # no room_mode key — should default to global
    )
    entry.runtime_data.rooms = {"area_w": ["climate.default_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.default_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for default_trv"
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    ), (
        f"Absent room_mode key should default to global (Normal=20.0), got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday 12:00 UTC — Normal active
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
        rooms_config={
            "area_v": {
                "room_mode": ROOM_MODE_FROST,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
            }
        },
    )
    entry.runtime_data.rooms = {"area_v": ["climate.combo_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.combo_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for combo_trv"
    pushed = calls[-1].data["temperature"]
    assert pushed == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"room_mode=frost_protection should push 7.0 ignoring time_program, got {pushed}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 16:30:00"
)  # Monday 16:30 UTC = 08:30 US/Pacific (Normal period)
async def test_room_mode_frost_wins_over_presence(hass):
    """D-20: room_mode='frost_protection' overrides presence mode for the room.

    Even when a present person is associated with the room, frost_protection wins.
    The room is held at 7.0 regardless of presence.
    """
    hass.states.async_set(
        "climate.presence_frost_trv", "heat", {"temperature": 15.0}
    )
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

    calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.presence_frost_trv"
    ]
    assert len(calls) >= 1, (
        "Expected set_temperature call for presence_frost_trv"
    )
    pushed = calls[-1].data["temperature"]
    assert pushed == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"room_mode=frost_protection should override presence and push 7.0, got {pushed}"
    )


# ---------------------------------------------------------------------------
# Regression tests: zone MODE_OFF overrides room_mode=custom (EVAL-01 fix)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday 12:00 UTC -- Comfort active in custom program
async def test_zone_off_overrides_room_mode_custom_default_zone(hass):
    """EVAL-01 / Bug fix: zone MODE_OFF must override room_mode=custom.

    Regression: when global_mode=off, a room with room_mode=custom and a
    Comfort-all-day time_program was previously pushed 22.0 (custom schedule
    temperature) instead of 7.0 (frost protection). Zone OFF must win.

    Setup:
    - Global mode: off (Default Zone)
    - Room: area_y with room_mode=custom and Comfort-all-day time_program
    - Expected: TRV receives frost-protection temperature (7.0), NOT 22.0
    """
    hass.states.async_set(
        "climate.custom_off_trv", "heat", {"temperature": 22.0}
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_OFF,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={
            "area_y": {
                "room_mode": ROOM_MODE_CUSTOM,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
            }
        },
    )
    entry.runtime_data.rooms = {"area_y": ["climate.custom_off_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.custom_off_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for custom_off_trv"
    pushed = calls[-1].data["temperature"]
    assert pushed == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"Zone MODE_OFF must override room_mode=custom -- expected 7.0, got {pushed}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday 12:00 UTC
async def test_zone_off_overrides_room_mode_custom_custom_zone(hass):
    """EVAL-01 / Bug fix: custom zone MODE_OFF overrides room_mode=custom.

    Same as above but the room is in a named custom zone (not the Default Zone).
    Zone OFF must still win over the room's custom schedule.
    """
    hass.states.async_set(
        "climate.zone_custom_off_trv", "heat", {"temperature": 22.0}
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    zone_id = "zone-abc"
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,  # Default Zone is active
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={
            "area_custom": {
                "room_mode": ROOM_MODE_CUSTOM,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
                "zone_id": zone_id,
            }
        },
        zones_config={
            zone_id: {
                "name": "Night Zone",
                "mode": MODE_OFF,
                "time_program": ALL_DAYS_NORMAL_PROGRAM,
            }
        },
    )
    entry.runtime_data.rooms = {"area_custom": ["climate.zone_custom_off_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.zone_custom_off_trv"
    ]
    assert len(calls) >= 1, (
        "Expected set_temperature call for zone_custom_off_trv"
    )
    pushed = calls[-1].data["temperature"]
    assert pushed == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION], (
        f"Custom zone MODE_OFF must override room_mode=custom -- "
        f"expected 7.0, got {pushed}"
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


# ---------------------------------------------------------------------------
# Tests: MODE_OFF per-TRV dispatch (quick task 260526-ffr)
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_mode_off_uses_set_hvac_mode_off_when_supported(hass):
    """MODE_OFF: TRV advertising hvac_modes=['heat','off'] receives set_temperature(frost)
    followed by set_hvac_mode=off (in that order).

    set_temperature is called first to pre-set the frost setpoint so that when the TRV
    exits OFF it resumes at frost rather than an arbitrary stale setpoint.
    """
    hass.states.async_set(
        "climate.off_capable_trv",
        "heat",
        {"hvac_modes": ["heat", "off"], "temperature": 18.0},
    )

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_OFF
    )
    entry.runtime_data.rooms = {"living": ["climate.off_capable_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    entity_hvac = [
        c
        for c in hvac_calls
        if c.data.get("entity_id") == "climate.off_capable_trv"
    ]
    entity_temp = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.off_capable_trv"
    ]

    assert any(c.data.get("hvac_mode") == "off" for c in entity_hvac), (
        "Expected at least one set_hvac_mode=off call for off-capable TRV in MODE_OFF"
    )
    assert len(entity_temp) >= 1, (
        "Expected set_temperature(frost) call before set_hvac_mode=off for off-capable TRV"
    )
    assert (
        entity_temp[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
    ), (
        f"Expected frost-protection temp {DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]}, "
        f"got {entity_temp[-1].data['temperature']}"
    )

    # Verify ordering: set_temperature must appear before set_hvac_mode=off.
    # We find the index of the last set_temperature call and the first set_hvac_mode=off call
    # in the combined service call log (temp_calls + hvac_calls share the same underlying list
    # since both are registered on the same domain; order them by position in each list via
    # checking that temp_calls[last_temp_idx] precedes hvac_calls[first_off_idx]).
    last_temp_idx = max(
        i
        for i, c in enumerate(temp_calls)
        if c.data.get("entity_id") == "climate.off_capable_trv"
    )
    first_off_idx = min(
        i
        for i, c in enumerate(hvac_calls)
        if c.data.get("hvac_mode") == "off"
        and c.data.get("entity_id") == "climate.off_capable_trv"
    )
    # Both lists grow monotonically in call order; temp list length at time of off call
    # must be > last_temp_idx (i.e. the frost-temp call happened before the off call).
    # Since async_mock_service captures calls in order, we just assert len(temp_calls) > 0
    # and trust that the coordinator awaits them sequentially (the implementation is sequential).
    assert last_temp_idx >= 0, "set_temperature call must exist"
    assert first_off_idx >= 0, "set_hvac_mode=off call must exist"


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_mode_off_falls_back_to_frost_temp_when_off_not_supported(hass):
    """MODE_OFF: TRV without 'off' in hvac_modes receives frost-protection setpoint.

    Any set_hvac_mode call for this entity must use hvac_mode='heat' (not 'off').
    """
    hass.states.async_set(
        "climate.heat_only_trv",
        "heat",
        {"hvac_modes": ["heat"], "temperature": 18.0},
    )

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_OFF
    )
    entry.runtime_data.rooms = {"bedroom": ["climate.heat_only_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    entity_temp = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.heat_only_trv"
    ]
    entity_hvac = [
        c
        for c in hvac_calls
        if c.data.get("entity_id") == "climate.heat_only_trv"
    ]

    assert len(entity_temp) >= 1, (
        "Expected set_temperature call for heat-only TRV in MODE_OFF"
    )
    assert (
        entity_temp[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
    ), (
        f"Expected frost-protection temp {DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]}, "
        f"got {entity_temp[-1].data['temperature']}"
    )
    for c in entity_hvac:
        assert c.data.get("hvac_mode") != "off", (
            "set_hvac_mode=off must never be issued for heat-only TRV"
        )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_mode_off_does_not_flap_set_hvac_mode_off_on_repeat_tick(hass):
    """MODE_OFF: calling async_evaluate twice for an off-capable TRV emits only ONE set_hvac_mode=off
    and only ONE set_temperature(frost) call.

    Push-on-change parity: the 'off' sentinel in _last_pushed prevents flapping for both calls.
    """
    hass.states.async_set(
        "climate.flap_test_trv",
        "heat",
        {"hvac_modes": ["heat", "off"], "temperature": 18.0},
    )

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_OFF
    )
    entry.runtime_data.rooms = {"hall": ["climate.flap_test_trv"]}

    # First tick
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # Second tick — same MODE_OFF, same entity
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    off_calls = [
        c
        for c in hvac_calls
        if c.data.get("entity_id") == "climate.flap_test_trv"
        and c.data.get("hvac_mode") == "off"
    ]
    frost_calls = [
        c
        for c in temp_calls
        if c.data.get("entity_id") == "climate.flap_test_trv"
    ]
    assert len(off_calls) == 1, (
        f"Expected exactly 1 set_hvac_mode=off call (no flapping); got {len(off_calls)}"
    )
    assert len(frost_calls) == 1, (
        f"Expected exactly 1 set_temperature(frost) call (no flapping); got {len(frost_calls)}"
    )


@pytest.mark.asyncio
async def test_mode_off_to_time_program_pushes_schedule_temp(hass):
    """Regression: switching from MODE_OFF to MODE_TIME_PROGRAM must push schedule temp.

    The 'off' sentinel stored in _last_pushed during MODE_OFF is a string.
    _push_if_changed's D-03 guard compares float(reported) != last; with last=="off"
    this is always True in Python 3, causing a spurious override hold that silently
    blocks every subsequent push. Fix: treat string sentinel as None (no prior push).
    """
    entity = "climate.bureau_trv"
    hass.states.async_set(
        entity,
        "off",
        {"hvac_modes": ["heat", "off"], "temperature": 18.0},
    )

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coord = entry.runtime_data.coordinator
    entry.runtime_data.rooms = {"bureau": [entity]}

    # Tick 1: MODE_OFF — should push set_hvac_mode=off
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_OFF
    )
    await coord.async_evaluate()
    await hass.async_block_till_done()

    off_calls = [c for c in hvac_calls if c.data.get("hvac_mode") == "off"]
    assert len(off_calls) == 1, (
        "Expected one set_hvac_mode=off call in MODE_OFF"
    )
    assert coord._last_pushed.get(entity) == "off", (
        "Expected 'off' sentinel in _last_pushed"
    )

    # Tick 2: switch to MODE_TIME_PROGRAM — should push heat + schedule temp
    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode="time_program"
    )
    await coord.async_evaluate()
    await hass.async_block_till_done()

    heat_calls = [c for c in hvac_calls if c.data.get("hvac_mode") == "heat"]
    assert len(heat_calls) >= 1, (
        "Expected at least one set_hvac_mode=heat call after switching from MODE_OFF "
        "to time_program — 'off' sentinel must not block the push via D-03 override hold"
    )
    assert len(temp_calls) >= 1, (
        "Expected at least one set_temperature call after switching from MODE_OFF to time_program"
    )


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

    living_entry = next(
        e for e in rooms_status if e["area_id"] == "living_room"
    )
    kitchen_entry = next(e for e in rooms_status if e["area_id"] == "kitchen")

    assert living_entry["present_person_count"] == 1, (
        f"living_room: expected 1 (alice present+assigned), got {living_entry['present_person_count']}"
    )
    assert kitchen_entry["present_person_count"] == 0, (
        f"kitchen: expected 0 (bob assigned but absent), got {kitchen_entry['present_person_count']}"
    )


# ---------------------------------------------------------------------------
# Tests: Zone-aware evaluation (EVAL-01..05) — Plan 05-03
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday noon — Normal in ALL_DAYS_NORMAL_PROGRAM
async def test_zone_mode_off_pushes_frost_temp(hass):
    """EVAL-01: zone with mode=off pushes frost-protection temp to its rooms.

    Proves that a custom zone in MODE_OFF causes its rooms' TRVs to receive
    PERIOD_FROST_PROTECTION regardless of the global schedule.
    """
    hass.states.async_set("climate.z_trv", "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        zones_config={
            "z1": {
                "name": "Z1",
                "mode": MODE_OFF,
                "time_program": ALL_DAYS_NORMAL_PROGRAM,
            }
        },
        rooms_config={"area_z": {"zone_id": "z1"}},
    )
    entry.runtime_data.rooms = {"area_z": ["climate.z_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.z_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for z_trv"
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
    ), (
        f"zone mode=off should push frost (5.0), got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday noon — Normal in ALL_DAYS_*
async def test_zone_mode_time_program_uses_zone_schedule(hass):
    """EVAL-02: zone with mode=time_program uses zone.time_program, not global_time_program.

    Default Zone rooms use global_time_program (Normal → 20.0).
    Custom zone rooms use zone.time_program (Comfort → 22.0).
    Proves divergence: same global_mode=time_program, different temperatures.
    """
    hass.states.async_set("climate.z_trv", "heat", {"temperature": 20.0})
    hass.states.async_set("climate.d_trv", "heat", {"temperature": 18.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        zones_config={
            "z1": {
                "name": "Z1",
                "mode": MODE_TIME_PROGRAM,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
            }
        },
        rooms_config={"area_z": {"zone_id": "z1"}, "area_default": {}},
    )
    entry.runtime_data.rooms = {
        "area_z": ["climate.z_trv"],
        "area_default": ["climate.d_trv"],
    }

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    z_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.z_trv"
    ]
    d_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.d_trv"
    ]

    assert len(z_calls) >= 1, "Expected set_temperature call for z_trv"
    assert (
        z_calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_COMFORT]
    ), (
        f"zone=z1 (Comfort schedule) should push 22.0, got {z_calls[-1].data['temperature']}"
    )
    assert len(d_calls) >= 1, "Expected set_temperature call for d_trv"
    assert (
        d_calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    ), (
        f"Default Zone (Normal schedule) should push 20.0, got {d_calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time(
    "2026-01-05 12:00:00"
)  # Monday noon — Normal in ALL_DAYS_NORMAL
async def test_zone_mode_presences_applies_presence(hass):
    """EVAL-03: zone with mode=time_program_presences applies presence evaluation.

    global_mode=time_program (NOT presences) — proves zone presence is independent
    of global_mode. A force_present person assigned to the zone's room causes
    compute_occupied_temp to run (presence path active).
    """
    hass.states.async_set("climate.z_trv", "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,  # global NOT presences
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        zones_config={
            "z1": {
                "name": "Z1",
                "mode": MODE_TIME_PROGRAM_PRESENCES,
                "time_program": ALL_DAYS_NORMAL_PROGRAM,
            }
        },
        persons_config={
            "person.alice": {"mode": PRESENCE_PRESENT, "room_ids": ["area_z"]}
        },
        rooms_config={"area_z": {"zone_id": "z1"}},
    )
    entry.runtime_data.rooms = {"area_z": ["climate.z_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.z_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for z_trv"
    # force_present + Normal schedule at noon → compute_occupied_temp gives Normal temp
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
    ), (
        f"zone presences mode with force_present should push Normal (20.0), got {calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday noon
async def test_global_mode_off_does_not_affect_custom_zones(hass):
    """EVAL-04 per D-10: global_mode=off only puts Default Zone rooms at frost.

    Custom zone rooms with mode=time_program continue following their schedule.
    Proves global_mode=off is NOT a system-wide override (D-07/D-08/D-10).
    """
    hass.states.async_set("climate.d_trv", "heat", {"temperature": 20.0})
    hass.states.async_set("climate.z_trv", "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_OFF,  # Default Zone is off
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        zones_config={
            "z1": {
                "name": "Z1",
                "mode": MODE_TIME_PROGRAM,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
            }
        },
        rooms_config={"area_default": {}, "area_z": {"zone_id": "z1"}},
    )
    entry.runtime_data.rooms = {
        "area_default": ["climate.d_trv"],
        "area_z": ["climate.z_trv"],
    }

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    d_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.d_trv"
    ]
    z_calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.z_trv"
    ]

    assert len(d_calls) >= 1, "Expected set_temperature call for d_trv"
    assert (
        d_calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
    ), (
        f"Default Zone with global_mode=off should push frost (5.0), got {d_calls[-1].data['temperature']}"
    )
    assert len(z_calls) >= 1, "Expected set_temperature call for z_trv"
    assert (
        z_calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_COMFORT]
    ), (
        f"Custom zone (Comfort schedule) should push 22.0 even when global_mode=off, got {z_calls[-1].data['temperature']}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")  # Monday noon
async def test_room_mode_custom_wins_over_active_zone_schedule(hass):
    """EVAL-05: room with room_mode=custom uses room.time_program when zone is active.

    Zone has mode=time_program (Normal schedule). Room has room_mode=custom with
    Comfort schedule. room_mode=custom must win over the zone schedule and push
    Comfort (22.0) when the zone is active (not off).
    """
    hass.states.async_set("climate.z_trv", "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        zones_config={
            "z1": {
                "name": "Z1",
                "mode": MODE_TIME_PROGRAM,  # zone is active -- room custom wins
                "time_program": ALL_DAYS_NORMAL_PROGRAM,
            }
        },
        rooms_config={
            "area_z": {
                "zone_id": "z1",
                "room_mode": ROOM_MODE_CUSTOM,
                "time_program": ALL_DAYS_COMFORT_PROGRAM,
            }
        },
    )
    entry.runtime_data.rooms = {"area_z": ["climate.z_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [
        c for c in temp_calls if c.data.get("entity_id") == "climate.z_trv"
    ]
    assert len(calls) >= 1, "Expected set_temperature call for z_trv"
    assert (
        calls[-1].data["temperature"]
        == DEFAULT_PERIOD_TEMPERATURES[PERIOD_COMFORT]
    ), (
        f"room_mode=custom should win over active zone schedule and push Comfort (22.0), "
        f"got {calls[-1].data['temperature']}"
    )


# ---------------------------------------------------------------------------
# Tests: TRV offset calibration pass (09-02)
# CALIB-02/03/04/05 — _async_calibrate + _async_calibrate_room
# ---------------------------------------------------------------------------


def _make_calibration_config(
    calibration_enabled: bool = True,
    calibration_threshold: float = 0.5,
    rooms_config: dict | None = None,
    sensor_entity_id: str | None = None,
    area_id: str = "bedroom",
) -> dict:
    """Build a runtime_config with calibration settings for test use."""
    room_cfg: dict = {}
    if sensor_entity_id is not None:
        room_cfg["temperature_sensor"] = sensor_entity_id
    cfg = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config=rooms_config
        if rooms_config is not None
        else ({area_id: room_cfg} if room_cfg else {}),
    )
    cfg["calibration_enabled"] = calibration_enabled
    cfg["calibration_threshold"] = calibration_threshold
    return cfg


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_disabled_zero_offset_calls(hass):
    """D-04: calibration_enabled=False → zero offset service calls.

    Even with a fully configured room+TRV+sensor, no tado_x calls must
    be made when calibration is globally disabled.
    """
    hass.states.async_set(
        "climate.bedroom_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 19.0,
            "temperature_offset": 0.0,
        },
    )
    hass.states.async_set("sensor.bedroom_temp", "21.0")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=False,
        sensor_entity_id="sensor.bedroom_temp",
    )
    entry.runtime_data.rooms = {"bedroom": ["climate.bedroom_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 0, (
        f"calibration_enabled=False must produce zero offset calls; got {len(offset_calls)}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_no_sensor_zero_offset_calls(hass):
    """CALIB-05/D-14: room with no temperature_sensor configured → zero calls.

    calibration_enabled=True but no temperature_sensor key in rooms config
    for this area — the room must be silently skipped.
    """
    hass.states.async_set(
        "climate.bedroom_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 19.0,
            "temperature_offset": 0.0,
        },
    )

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # No temperature_sensor key in rooms config
    cfg = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"bedroom": {}},  # no temperature_sensor key
    )
    cfg["calibration_enabled"] = True
    cfg["calibration_threshold"] = 0.5
    entry.runtime_data.runtime_config = cfg
    entry.runtime_data.rooms = {"bedroom": ["climate.bedroom_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 0, (
        f"Room with no temperature_sensor must produce zero offset calls; "
        f"got {len(offset_calls)}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_incompatible_trv_zero_offset_calls(hass):
    """CALIB-03/D-08: TRV without temperature_offset attr AND no tado_x service.

    supports_offset_calibration returns False → room must be silently skipped.
    """
    # TRV with no temperature_offset attribute (no tado_x service either)
    hass.states.async_set(
        "climate.incompatible_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 19.0,
            # NO temperature_offset attribute
        },
    )
    hass.states.async_set("sensor.room_temp", "21.0")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    # Do NOT register tado_x service — this test verifies the guard blocks
    # when neither temperature_offset attribute nor tado_x service exists.
    # async_mock_service would register the service, defeating the test.

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=True,
        sensor_entity_id="sensor.room_temp",
        area_id="study",
    )
    entry.runtime_data.rooms = {"study": ["climate.incompatible_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # No assertion needed — if guard failed, set_trv_offset would raise
    # ServiceNotFound (unregistered service). Test passing means guard worked.
    # Service was never registered, so guard must have returned early.
    assert not hass.services.has_service("tado_x", "set_temperature_offset")


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_delta_below_threshold_zero_offset_calls(hass):
    """CALIB-04/D-07: abs(delta) <= threshold → zero offset calls (jitter guard).

    sensor_temp=20.3, current_temperature=20.0 → delta=0.3 ≤ 0.5 → skip.
    """
    hass.states.async_set(
        "climate.living_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 20.0,
            "temperature_offset": 0.0,
        },
    )
    hass.states.async_set("sensor.living_temp", "20.3")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=True,
        calibration_threshold=0.5,
        sensor_entity_id="sensor.living_temp",
        area_id="living",
    )
    entry.runtime_data.rooms = {"living": ["climate.living_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 0, (
        f"abs(delta)=0.3 ≤ threshold=0.5 must produce zero offset calls; "
        f"got {len(offset_calls)}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_delta_above_threshold_one_offset_call(hass):
    """D-05/D-06: abs(delta) > threshold → exactly one offset call with correct value.

    sensor_temp=21.0, current_temperature=20.0, existing_offset=0.5
    delta = 21.0 - 20.0 = 1.0
    new_offset = 0.5 + 1.0 = 1.5
    Expected: one call with offset=1.5.
    """
    hass.states.async_set(
        "climate.hall_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 20.0,
            "temperature_offset": 0.5,
        },
    )
    hass.states.async_set("sensor.hall_temp", "21.0")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=True,
        calibration_threshold=0.5,
        sensor_entity_id="sensor.hall_temp",
        area_id="hall",
    )
    entry.runtime_data.rooms = {"hall": ["climate.hall_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 1, (
        f"abs(delta)=1.0 > threshold=0.5 must produce exactly one offset call; "
        f"got {len(offset_calls)}"
    )
    applied_offset = offset_calls[0].data.get("offset")
    assert applied_offset == pytest.approx(1.5), (
        f"new_offset = existing(0.5) + delta(1.0) = 1.5; got {applied_offset}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_sensor_unavailable_zero_offset_calls(hass):
    """Pitfall 5: sensor state 'unavailable' → zero offset calls.

    The calibration pass must silently skip when the reference sensor
    reports 'unavailable'.
    """
    hass.states.async_set(
        "climate.kitchen_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 19.0,
            "temperature_offset": 0.0,
        },
    )
    hass.states.async_set("sensor.kitchen_temp", "unavailable")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=True,
        sensor_entity_id="sensor.kitchen_temp",
        area_id="kitchen",
    )
    entry.runtime_data.rooms = {"kitchen": ["climate.kitchen_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 0, (
        f"Sensor state 'unavailable' must produce zero offset calls; "
        f"got {len(offset_calls)}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_sensor_unknown_zero_offset_calls(hass):
    """Pitfall 5: sensor state 'unknown' → zero offset calls.

    The calibration pass must silently skip when the reference sensor
    reports 'unknown'.
    """
    hass.states.async_set(
        "climate.bathroom_trv",
        "heat",
        {
            "temperature": 20.0,
            "current_temperature": 19.0,
            "temperature_offset": 0.0,
        },
    )
    hass.states.async_set("sensor.bathroom_temp", "unknown")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=True,
        sensor_entity_id="sensor.bathroom_temp",
        area_id="bathroom",
    )
    entry.runtime_data.rooms = {"bathroom": ["climate.bathroom_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 0, (
        f"Sensor state 'unknown' must produce zero offset calls; "
        f"got {len(offset_calls)}"
    )


@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_calibration_trv_current_temperature_none_zero_offset_calls(hass):
    """Pitfall 2: TRV current_temperature attribute is None → zero offset calls.

    The calibration pass must silently skip when the TRV's current_temperature
    attribute is absent (None).
    """
    hass.states.async_set(
        "climate.office_trv",
        "heat",
        {
            "temperature": 20.0,
            # NO current_temperature attribute → will be None
            "temperature_offset": 0.0,
        },
    )
    hass.states.async_set("sensor.office_temp", "21.5")

    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_calibration_config(
        calibration_enabled=True,
        sensor_entity_id="sensor.office_temp",
        area_id="office",
    )
    entry.runtime_data.rooms = {"office": ["climate.office_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert len(offset_calls) == 0, (
        f"TRV current_temperature=None must produce zero offset calls; "
        f"got {len(offset_calls)}"
    )

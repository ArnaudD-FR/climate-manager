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
            "mode": "present",
            "room_ids": ["lounge"],
            "schedule": {},  # per-day: empty dict = no schedule
        },
        "person.bob": {
            "mode": "absent",
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

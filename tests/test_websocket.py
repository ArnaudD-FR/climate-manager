"""Tests for Climate Manager WebSocket command handlers.

Tests:
- get_config returns runtime_config containing "global_mode"
- set_global_mode mode=off succeeds and persists to runtime_config
- set_time_program with a partial program (missing day keys) returns a WS error
  and does NOT mutate runtime_config["global_time_program"]

All tests use MockConfigEntry + hass_ws_client following the scaffold from test_coordinator.py.
The hass_ws_client fixture provides an authenticated WebSocket client via
pytest-homeassistant-custom-component.
"""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    _DEFAULT_DAILY_PROGRAM,
)


async def _setup_entry(hass) -> MockConfigEntry:
    """Helper: set up the integration entry and return it.

    Mirrors the scaffold from test_coordinator.py (lines 84-127).
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# ---------------------------------------------------------------------------
# Test 1: get_config returns runtime_config
# ---------------------------------------------------------------------------


async def test_ws_get_config_returns_runtime_config(hass, hass_ws_client):
    """get_config WS command returns runtime_config containing 'global_mode'.

    Verifies the read path: panel can fetch the full config on startup.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "global_mode" in msg["result"]
    # Fresh install defaults to MODE_TIME_PROGRAM
    assert msg["result"]["global_mode"] == MODE_TIME_PROGRAM


# ---------------------------------------------------------------------------
# Test 2: set_global_mode persists and updates runtime_config
# ---------------------------------------------------------------------------


async def test_ws_set_global_mode_persists_and_evaluates(hass, hass_ws_client):
    """set_global_mode mode=off returns success and persists to runtime_config.

    Verifies the write-then-evaluate pattern: after a successful set_global_mode,
    entry.runtime_data.runtime_config["global_mode"] must equal MODE_OFF.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_global_mode", "mode": MODE_OFF}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    assert entry.runtime_data.runtime_config["global_mode"] == MODE_OFF


# ---------------------------------------------------------------------------
# Test 3: set_time_program rejects a partial program (missing day keys)
# ---------------------------------------------------------------------------


async def test_ws_set_time_program_rejects_partial(hass, hass_ws_client):
    """set_time_program with a program missing day keys returns a WS error.

    Verifies T-03-05: validate_daily_program gate sends send_error and returns
    BEFORE any save/evaluate — the original global_time_program is unchanged.
    """
    entry = await _setup_entry(hass)

    # Capture original program (should be the default empty per-day dict)
    original_program = dict(entry.runtime_data.runtime_config["global_time_program"])

    # Send a partial program missing most day keys (only "mon" present)
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_time_program",
            "program": {"mon": []},  # missing tue, wed, thu, fri, sat, sun
        }
    )
    msg = await client.receive_json()

    # Must be an error response (success False or error type)
    assert msg.get("success") is False or msg.get("type") == "result" and msg.get("success") is False

    # global_time_program must be unchanged — T-03-05 validation gate
    assert entry.runtime_data.runtime_config["global_time_program"] == original_program


# ---------------------------------------------------------------------------
# Test 4: D-24 — get_status rooms_status includes present_person_count
# ---------------------------------------------------------------------------


async def test_ws_get_status_includes_present_person_count(hass, hass_ws_client):
    """D-24: get_status returns rooms_status entries with present_person_count.

    Seeded: living_room has alice (present) assigned; kitchen has no present persons.
    Expected: living_room.present_person_count == 1, kitchen.present_person_count == 0.
    """
    entry = await _setup_entry(hass)

    # Seed rooms, persons config, and coordinator state
    entry.runtime_data.rooms = {"living_room": ["climate.x"], "kitchen": ["climate.y"]}
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {"room_ids": ["living_room"]},
    }
    entry.runtime_data.coordinator._last_present_persons = ["person.alice"]

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_status"})
    msg = await client.receive_json()

    assert msg["success"] is True

    rooms_status = msg["result"]["rooms_status"]

    # Every entry must have the key
    for room_entry in rooms_status:
        assert "present_person_count" in room_entry, (
            f"present_person_count missing from {room_entry['area_id']}"
        )

    living_entry = next(e for e in rooms_status if e["area_id"] == "living_room")
    kitchen_entry = next(e for e in rooms_status if e["area_id"] == "kitchen")

    assert living_entry["present_person_count"] == 1
    assert kitchen_entry["present_person_count"] == 0


# ---------------------------------------------------------------------------
# Tests 5-6: D-25 — get_config includes climate_entities list
# ---------------------------------------------------------------------------


async def test_ws_get_config_includes_climate_entities(hass, hass_ws_client):
    """D-25: get_config returns climate_entities list with all registered climate entity IDs.

    Registers a fake climate entity via entity registry, then verifies:
    - climate_entities key is present
    - every element starts with 'climate.'
    - the registered entity ID is in the list
    - the list is sorted
    - original runtime_config keys (global_mode, period_temperatures) are still present
    """
    from homeassistant.helpers import entity_registry as er

    await _setup_entry(hass)

    # Register a fake climate entity
    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create("climate", "test", "fake_trv")

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "climate_entities" in msg["result"]

    climate_entities = msg["result"]["climate_entities"]
    assert isinstance(climate_entities, list)
    for eid in climate_entities:
        assert eid.startswith("climate."), f"Expected climate. prefix, got: {eid}"

    # The registered fake entity must appear
    assert "climate.test_fake_trv" in climate_entities

    # Must be sorted
    assert climate_entities == sorted(climate_entities)

    # Original runtime_config keys still present alongside climate_entities
    assert "global_mode" in msg["result"]
    assert "period_temperatures" in msg["result"]


async def test_ws_get_config_climate_entities_empty_when_none_registered(hass, hass_ws_client):
    """D-25: get_config returns climate_entities=[] when no climate entities are registered."""
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "climate_entities" in msg["result"]
    assert msg["result"]["climate_entities"] == []


# ---------------------------------------------------------------------------
# Tests 7-8: reset_period_temperatures and reset_time_program WS commands
# ---------------------------------------------------------------------------


async def test_ws_reset_period_temperatures_writes_defaults(hass, hass_ws_client):
    """reset_period_temperatures resets period_temperatures to DEFAULT_PERIOD_TEMPERATURES.

    Mutates period_temperatures to non-default values first, then sends the reset
    command and asserts the result matches DEFAULT_PERIOD_TEMPERATURES from const.py.
    """
    entry = await _setup_entry(hass)

    # Mutate to obviously non-default values
    entry.runtime_data.runtime_config["period_temperatures"] = {
        "frost_protection": 99.0,
        "reduced": 99.0,
        "normal": 99.0,
        "comfort": 99.0,
    }

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/reset_period_temperatures"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Must match the module-level defaults exactly
    assert entry.runtime_data.runtime_config["period_temperatures"] == DEFAULT_PERIOD_TEMPERATURES

    # Verify no reference sharing: mutating runtime_config must not affect the constant
    entry.runtime_data.runtime_config["period_temperatures"]["frost_protection"] = 1.0
    assert DEFAULT_PERIOD_TEMPERATURES["frost_protection"] == 5.0


async def test_ws_reset_time_program_writes_defaults(hass, hass_ws_client):
    """reset_time_program resets global_time_program to _DEFAULT_DAILY_PROGRAM.

    Mutates global_time_program to a 1-day stub first, then sends the reset command
    and asserts the resulting program has all 7 day keys with weekday/weekend splits
    matching the const.py defaults.
    """
    entry = await _setup_entry(hass)

    # Mutate to a 1-day stub (missing tue..sun)
    entry.runtime_data.runtime_config["global_time_program"] = {
        "mon": [{"start": "00:00", "mode": "normal"}],
    }

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/reset_time_program"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    program = entry.runtime_data.runtime_config["global_time_program"]

    # Must have all 7 day keys
    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        assert day in program, f"Missing day key: {day}"

    # Weekdays: 5 periods (morning + evening normal blocks)
    expected_weekday_starts = ("00:00", "06:00", "08:00", "17:00", "22:00")
    for day in ("mon", "tue", "wed", "thu", "fri"):
        starts = tuple(p["start"] for p in program[day])
        assert starts == expected_weekday_starts, f"Day {day}: expected starts {expected_weekday_starts}, got {starts}"

    # Weekends: 3 periods (full-day normal)
    expected_weekend_starts = ("00:00", "06:00", "22:00")
    for day in ("sat", "sun"):
        starts = tuple(p["start"] for p in program[day])
        assert starts == expected_weekend_starts, f"Day {day}: expected starts {expected_weekend_starts}, got {starts}"

    # Must equal the module-level default (deep equality check)
    assert program == _DEFAULT_DAILY_PROGRAM

    # Verify deep copy: mutating runtime_config must not affect the constant
    program["mon"][0]["mode"] = "comfort"
    assert _DEFAULT_DAILY_PROGRAM["mon"][0]["mode"] == "reduced"

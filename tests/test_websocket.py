"""Tests for Climate Manager WebSocket command handlers.

Tests:
- get_config returns runtime_config containing "default_zone"
- set_global_mode command is no longer registered (removed in D-08)
- set_time_program with a partial program (missing day keys) returns a WS error
  and does NOT mutate runtime_config["default_zone"]["time_program"]
- create_zone returns zone config and persists to runtime_config
- rename_zone updates custom zone name and default_zone.name
- set_zone_mode updates zone mode (custom + default) and rejects invalid modes
- set_zone_mode with zone_id="default" writes default_zone.mode (D-08)
- reset_zone_time_program with zone_id="default" resets default_zone.time_program (D-09)
- reset_time_program command is no longer registered (removed in D-09)
- reset_room_to_default_zone_program replaces reset_room_to_global_program (D-10)
- set_zone_preheat with zone_id="default" writes default_zone.preheat_enabled (D-11)
- rename_zone with zone_id="default" writes default_zone.name (D-11)
- get_status returns zones.default.mode with no top-level global_mode (D-07)

All tests use MockConfigEntry + hass_ws_client following the scaffold from test_coordinator.py.
The hass_ws_client fixture provides an authenticated WebSocket client via
pytest-homeassistant-custom-component.
"""

import copy

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    _DEFAULT_DAILY_PROGRAM,
)

# Presence schedule: Mon–Fri present 08:00–22:00, absent otherwise; Sat–Sun absent
# Inline copy to keep this test file self-contained (same as test_schedule.py).
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
# Test 1: get_config returns runtime_config with default_zone (Phase 14, D-01)
# ---------------------------------------------------------------------------


async def test_ws_get_config_returns_runtime_config(hass, hass_ws_client):
    """get_config WS command returns runtime_config containing 'default_zone'.

    Phase 14 (D-01): default_zone replaces global_mode/global_time_program
    flat keys. Verifies the read path: panel can fetch the full config on
    startup with the new schema.
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "default_zone" in msg["result"]
    # Fresh install defaults to MODE_TIME_PROGRAM
    assert msg["result"]["default_zone"]["mode"] == MODE_TIME_PROGRAM
    # Old flat keys must be absent (D-08)
    assert "global_mode" not in msg["result"]


# ---------------------------------------------------------------------------
# Test 2: set_global_mode command is no longer registered (D-08)
# ---------------------------------------------------------------------------


async def test_ws_set_global_mode_is_removed(hass, hass_ws_client):
    """D-08: set_global_mode command is no longer registered.

    Sending the removed command must return an error (unknown command).
    The mode must not appear as a top-level key in runtime_config.
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_global_mode", "mode": MODE_OFF}
    )
    msg = await client.receive_json()

    # Must be an error (command not found / unknown command)
    assert msg.get("success") is False


# ---------------------------------------------------------------------------
# Test 3: set_time_program rejects a partial program (missing day keys)
# ---------------------------------------------------------------------------


async def test_ws_set_time_program_rejects_partial(hass, hass_ws_client):
    """set_time_program with a program missing day keys returns a WS error.

    Verifies T-03-05: validate_daily_program gate sends send_error and returns
    BEFORE any save/evaluate — the original default_zone.time_program is
    unchanged (Phase 14: global_time_program no longer exists as flat key).
    """
    entry = await _setup_entry(hass)

    # Capture original program from default_zone (new schema)
    original_program = dict(
        entry.runtime_data.runtime_config["default_zone"]["time_program"]
    )

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
    assert (
        msg.get("success") is False
        or msg.get("type") == "result"
        and msg.get("success") is False
    )

    # default_zone.time_program must be unchanged — T-03-05 validation gate
    assert (
        entry.runtime_data.runtime_config["default_zone"]["time_program"]
        == original_program
    )


# ---------------------------------------------------------------------------
# Test 4: D-07 — get_status returns zones dict with no top-level global_mode
# ---------------------------------------------------------------------------


async def test_ws_get_status_returns_zones_dict_not_global_mode(
    hass, hass_ws_client
):
    """D-07: get_status response contains zones.default.mode, no global_mode.

    Phase 14 (D-07): ws_get_status delegates to coordinator._build_status_payload().
    The response must contain zones.default.mode (not top-level global_mode or
    active_period).
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_status"})
    msg = await client.receive_json()

    assert msg["success"] is True
    result = msg["result"]

    # New shape: zones dict with "default" key
    assert "zones" in result, "get_status must return a 'zones' dict (D-07)"
    assert "default" in result["zones"], (
        "zones dict must contain 'default' key (D-06)"
    )
    assert "mode" in result["zones"]["default"], (
        "zones.default must have 'mode' key"
    )

    # Old shape: must NOT be present
    assert "global_mode" not in result, (
        "global_mode must be absent from get_status result (D-08)"
    )
    # Note: top-level active_period is removed; per-room active_period is
    # still valid inside rooms_status entries


# ---------------------------------------------------------------------------
# Test 4b: D-24 — get_status rooms_status includes present_person_count
# ---------------------------------------------------------------------------


async def test_ws_get_status_includes_present_person_count(
    hass, hass_ws_client
):
    """D-24: get_status returns rooms_status entries with present_person_count.

    Seeded: living_room has alice (present) assigned; kitchen has no present persons.
    Expected: living_room.present_person_count == 1, kitchen.present_person_count == 0.
    """
    entry = await _setup_entry(hass)

    # Seed rooms, persons config, and coordinator state
    entry.runtime_data.rooms = {
        "living_room": ["climate.x"],
        "kitchen": ["climate.y"],
    }
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

    living_entry = next(
        e for e in rooms_status if e["area_id"] == "living_room"
    )
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
        assert eid.startswith("climate."), (
            f"Expected climate. prefix, got: {eid}"
        )

    # The registered fake entity must appear
    assert "climate.test_fake_trv" in climate_entities

    # Must be sorted
    assert climate_entities == sorted(climate_entities)

    # Original runtime_config keys still present alongside climate_entities
    # Phase 14 (D-01): default_zone replaces global_mode flat key
    assert "default_zone" in msg["result"]
    assert "period_temperatures" in msg["result"]


async def test_ws_get_config_climate_entities_empty_when_none_registered(
    hass, hass_ws_client
):
    """D-25: get_config returns climate_entities=[] when no climate entities are registered."""
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "climate_entities" in msg["result"]
    assert msg["result"]["climate_entities"] == []


# ---------------------------------------------------------------------------
# Tests: get_config matter_entities + tado_x_entities (Plan 13-02, A2 Option A/C)
# ---------------------------------------------------------------------------


async def test_get_config_includes_matter_entities(hass, hass_ws_client):
    """get_config payload contains matter_entities listing Matter climate entities.

    Verifies A2 Option A/C: backend derives matter_entities list from entity
    registry platform check. Only climate.* entities with platform=="matter"
    are included; entities with other platforms are excluded.
    """
    from homeassistant.helpers import entity_registry as er

    await _setup_entry(hass)
    entity_reg = er.async_get(hass)

    # Register one Matter climate entity and one non-Matter climate entity
    matter_entry = entity_reg.async_get_or_create(
        "climate", "matter", "valve1_matter"
    )
    entity_reg.async_get_or_create("climate", "tado_x", "zone_lr")

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "matter_entities" in msg["result"], (
        "get_config must include matter_entities key"
    )
    matter_entities = msg["result"]["matter_entities"]
    assert isinstance(matter_entities, list)
    # The matter entity must be included
    assert matter_entry.entity_id in matter_entities
    # The tado_x entity must NOT be in matter_entities
    for eid in matter_entities:
        reg = entity_reg.async_get(eid)
        assert reg is not None and reg.platform == "matter", (
            f"Non-matter entity {eid} found in matter_entities"
        )


async def test_get_config_includes_tado_x_entities(hass, hass_ws_client):
    """get_config payload contains tado_x_entities listing tado_x climate entities.

    Verifies A2 Option A/C: backend derives tado_x_entities list from entity
    registry platform check. Only climate.* entities with platform=="tado_x"
    are included; entities with other platforms are excluded.
    """
    from homeassistant.helpers import entity_registry as er

    await _setup_entry(hass)
    entity_reg = er.async_get(hass)

    # Register one tado_x climate entity and one Matter climate entity
    tado_entry = entity_reg.async_get_or_create("climate", "tado_x", "zone_lr")
    entity_reg.async_get_or_create("climate", "matter", "valve1_matter")

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "tado_x_entities" in msg["result"], (
        "get_config must include tado_x_entities key"
    )
    tado_x_entities = msg["result"]["tado_x_entities"]
    assert isinstance(tado_x_entities, list)
    # The tado_x entity must be included
    assert tado_entry.entity_id in tado_x_entities
    # The matter entity must NOT be in tado_x_entities
    for eid in tado_x_entities:
        reg = entity_reg.async_get(eid)
        assert reg is not None and reg.platform == "tado_x", (
            f"Non-tado_x entity {eid} found in tado_x_entities"
        )


async def test_get_config_entity_lists_do_not_pollute_storage(
    hass, hass_ws_client
):
    """get_config derived lists do NOT mutate runtime_config or persisted store.

    Verifies T-13-06: matter_entities and tado_x_entities are derived from the
    entity registry and merged into a NEW payload dict — runtime_config is never
    mutated so the derived keys never pollute persistent storage (D-25 invariant).
    """
    from homeassistant.helpers import entity_registry as er

    entry = await _setup_entry(hass)
    entity_reg = er.async_get(hass)

    entity_reg.async_get_or_create("climate", "matter", "valve1_matter")
    entity_reg.async_get_or_create("climate", "tado_x", "zone_lr")

    # Capture a snapshot of runtime_config keys before the call
    keys_before = set(entry.runtime_data.runtime_config.keys())

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    # Both derived keys must appear in the payload
    assert "matter_entities" in msg["result"]
    assert "tado_x_entities" in msg["result"]

    # runtime_config must not have been mutated with derived keys
    keys_after = set(entry.runtime_data.runtime_config.keys())
    assert "matter_entities" not in keys_after, (
        "matter_entities must not be stored in runtime_config"
    )
    assert "tado_x_entities" not in keys_after, (
        "tado_x_entities must not be stored in runtime_config"
    )
    # No keys were added to runtime_config
    assert keys_after == keys_before


# ---------------------------------------------------------------------------
# Tests 7-8: reset_period_temperatures and reset_time_program WS commands
# ---------------------------------------------------------------------------


async def test_ws_reset_period_temperatures_writes_defaults(
    hass, hass_ws_client
):
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
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/reset_period_temperatures"}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Must match the module-level defaults exactly
    assert (
        entry.runtime_data.runtime_config["period_temperatures"]
        == DEFAULT_PERIOD_TEMPERATURES
    )

    # Verify no reference sharing: mutating runtime_config must not affect the constant
    entry.runtime_data.runtime_config["period_temperatures"][
        "frost_protection"
    ] = 1.0
    assert DEFAULT_PERIOD_TEMPERATURES["frost_protection"] == 5.0


async def test_ws_reset_time_program_is_removed(hass, hass_ws_client):
    """D-09: reset_time_program command is no longer registered.

    Phase 14 (D-09): reset_time_program is removed. The replacement is
    reset_zone_time_program(zone_id="default", target="default").
    Sending the removed command must return an error.
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/reset_time_program"})
    msg = await client.receive_json()

    # Must be an error (command not found / unknown command)
    assert msg.get("success") is False


# ---------------------------------------------------------------------------
# Test 9: reset_room_to_default_zone_program WS command (Phase 15 D-06)
# ---------------------------------------------------------------------------


async def test_ws_reset_room_to_default_zone_program_is_removed(
    hass, hass_ws_client
):
    """Phase 15 (D-06): reset_room_to_default_zone_program command is no
    longer registered.

    Sending the Phase 14 command name must return an error (both old and
    new names are now gone).
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reset_room_to_default_zone_program",
            "room_id": "room-a",
        }
    )
    msg = await client.receive_json()

    assert msg.get("success") is False


# ---------------------------------------------------------------------------
# Tests 10-14: Zone CRUD WS commands (Plan 05-01)
# ---------------------------------------------------------------------------


async def test_ws_create_zone_returns_zone_config(hass, hass_ws_client):
    """create_zone returns {zone_id, name, mode, time_program} and persists to runtime_config.

    Verifies D-01 (mode=time_program), D-02 (time_program copied from global),
    D-03 (full zone object returned), and D-06 (write-then-evaluate pattern).
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/create_zone", "name": "Living"}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    result = msg["result"]

    # Must return all required keys
    assert "zone_id" in result
    assert isinstance(result["zone_id"], str)
    assert result["name"] == "Living"
    assert result["mode"] == MODE_TIME_PROGRAM
    assert "time_program" in result
    assert isinstance(result["time_program"], dict)
    # time_program must have all 7 day keys
    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        assert day in result["time_program"], (
            f"time_program missing day key: {day}"
        )

    # Must persist to runtime_config
    zone_id = result["zone_id"]
    zones = entry.runtime_data.runtime_config.get("zones", {})
    assert zone_id in zones
    persisted = zones[zone_id]
    assert persisted["name"] == "Living"
    assert persisted["mode"] == MODE_TIME_PROGRAM
    assert persisted["time_program"] == result["time_program"]


async def test_ws_create_zone_copies_default_zone_program(hass, hass_ws_client):
    """create_zone deep-copies from the current default_zone.time_program (D-02/Pitfall 1).

    Phase 14 (Pitfall 1): create_zone must seed from
    default_zone["time_program"], not from global_time_program (removed).
    Mutates default_zone.time_program before sending — asserts the returned
    zone time_program reflects the mutation (copy of current state, not
    DEFAULT). Then mutates the returned program and asserts the source is
    unaffected (deepcopy).
    """
    entry = await _setup_entry(hass)

    # Mutate default_zone.time_program to a known sentinel before sending
    sentinel_period = [{"start": "00:00", "mode": "comfort"}]
    entry.runtime_data.runtime_config["default_zone"]["time_program"]["mon"] = (
        sentinel_period
    )

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/create_zone", "name": "TestZone"}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    result = msg["result"]

    # Returned time_program["mon"] must equal the sentinel (copied from
    # current default_zone.time_program)
    assert result["time_program"]["mon"] == sentinel_period

    # Deep-copy proof: mutating the returned program must NOT mutate
    # default_zone.time_program
    result["time_program"]["mon"].append({"start": "12:00", "mode": "reduced"})
    assert (
        entry.runtime_data.runtime_config["default_zone"]["time_program"]["mon"]
        == sentinel_period
    )


async def test_ws_rename_zone_custom(hass, hass_ws_client):
    """rename_zone updates the name of an existing custom zone.

    Verifies that rename_zone {zone_id, name: "New"} updates
    runtime_config["zones"][zone_id]["name"] and returns success.
    """
    entry = await _setup_entry(hass)

    # Seed a custom zone
    zone_id = "test-zone-uuid-1234"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Old",
        "mode": MODE_TIME_PROGRAM,
        "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/rename_zone", "zone_id": zone_id, "name": "New"}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    assert entry.runtime_data.runtime_config["zones"][zone_id]["name"] == "New"


async def test_ws_rename_zone_default(hass, hass_ws_client):
    """rename_zone with zone_id="default" writes default_zone.name (D-11).

    Phase 14 (D-11): "default" sentinel routes to
    runtime_config["default_zone"]["name"] (not the old flat
    default_zone_name key). Verifies the Default Zone sentinel branch never
    creates a "default" key in zones{}.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/rename_zone",
            "zone_id": "default",
            "name": "Maison",
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    # Phase 14 (D-11): Default Zone name must be updated in default_zone sub-dict
    assert entry.runtime_data.runtime_config["default_zone"]["name"] == "Maison"
    # Old flat key must NOT be used
    assert "default_zone_name" not in entry.runtime_data.runtime_config
    # Pitfall 3: "default" must NOT appear as a key in zones dict
    assert "default" not in entry.runtime_data.runtime_config.get("zones", {})


async def test_ws_set_zone_mode(hass, hass_ws_client):
    """set_zone_mode updates zone mode and rejects modes outside VALID_MODES (ZONE-08).

    Two sends on same client:
    1. Valid mode (MODE_OFF) — assert success and zones[zone_id]["mode"] == MODE_OFF
    2. Invalid mode ("bogus") — assert failure and zone mode is still MODE_OFF
    """
    entry = await _setup_entry(hass)

    # Seed a custom zone
    zone_id = "test-zone-uuid-1234"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "TestZone",
        "mode": MODE_TIME_PROGRAM,
        "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    }

    client = await hass_ws_client()

    # Send 1: valid mode change
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_mode",
            "zone_id": zone_id,
            "mode": MODE_OFF,
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    assert (
        entry.runtime_data.runtime_config["zones"][zone_id]["mode"] == MODE_OFF
    )

    # Send 2: invalid mode — vol schema must reject before handler runs
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_zone_mode", "zone_id": zone_id, "mode": "bogus"}
    )
    msg2 = await client.receive_json()

    assert msg2["success"] is False
    # Zone mode must be unchanged — schema rejection means no mutation
    assert (
        entry.runtime_data.runtime_config["zones"][zone_id]["mode"] == MODE_OFF
    )


async def test_ws_set_zone_mode_default_zone_success(hass, hass_ws_client):
    """D-08: set_zone_mode with zone_id="default" writes default_zone.mode.

    Phase 14 (D-08): set_zone_mode is extended to accept zone_id="default".
    Verifies:
    - result.success is True
    - default_zone.mode is updated in runtime_config
    - "default" never appears as a key in zones{}
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_mode",
            "zone_id": "default",
            "mode": MODE_OFF,
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    # D-08: mode must be written to default_zone sub-dict
    assert entry.runtime_data.runtime_config["default_zone"]["mode"] == MODE_OFF
    # Sentinel invariant: "default" must NOT appear as a key in zones{}
    assert "default" not in entry.runtime_data.runtime_config.get("zones", {})


async def test_ws_set_zone_mode_default_zone_invalid_mode_rejected(
    hass, hass_ws_client
):
    """D-08: set_zone_mode zone_id="default" invalid mode rejected by vol schema.

    T-14-05: vol.In(VALID_MODES) schema gate rejects invalid modes for all
    zone_ids including "default". default_zone.mode must remain unchanged.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_mode",
            "zone_id": "default",
            "mode": "bogus",
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is False
    # default_zone.mode must be unchanged (schema rejection = no mutation)
    assert (
        entry.runtime_data.runtime_config["default_zone"]["mode"]
        == MODE_TIME_PROGRAM
    )


# ---------------------------------------------------------------------------
# Tests 15-19: Zone delete/set_time_program/reset_time_program WS commands (Plan 05-02)
# ---------------------------------------------------------------------------


async def test_ws_delete_zone_migrates_rooms(hass, hass_ws_client):
    """delete_zone migrates rooms with zone_id to Default Zone (key removal, not None).

    Verifies ZONE-07:
    - zone is removed from runtime_config["zones"]
    - rooms that had zone_id=that_zone are migrated (zone_id key removed via pop)
    - rooms without zone_id are untouched
    """
    entry = await _setup_entry(hass)

    zone_id = "test-zone-1"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Test",
        "mode": MODE_TIME_PROGRAM,
        "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    }
    # Seed two rooms: one assigned to zone, one unassigned
    entry.runtime_data.runtime_config["rooms"] = {
        "area_a": {"zone_id": zone_id},
        "area_b": {},
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/delete_zone", "zone_id": zone_id}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Zone must be removed
    assert zone_id not in entry.runtime_data.runtime_config["zones"]

    # Migrated room must no longer have zone_id key (pop, not None)
    assert "zone_id" not in entry.runtime_data.runtime_config["rooms"]["area_a"]

    # Unaffected room must be untouched
    assert entry.runtime_data.runtime_config["rooms"]["area_b"] == {}


async def test_ws_delete_zone_not_found(hass, hass_ws_client):
    """delete_zone with unknown zone_id returns error and does not mutate runtime_config.

    Verifies ZONE-07 error path: ERR_NOT_FOUND when zone_id absent.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/delete_zone", "zone_id": "ghost"}
    )
    msg = await client.receive_json()

    assert msg["success"] is False
    # zones must be unchanged (empty after fresh setup)
    assert entry.runtime_data.runtime_config.get("zones", {}) == {}


async def test_ws_set_zone_time_program_rejects_partial(hass, hass_ws_client):
    """set_zone_time_program with partial program returns error and does NOT mutate zone.

    Verifies ZONE-09 / T-03-05 (Pitfall 6): validate_daily_program is called BEFORE
    any mutation — original time_program is unchanged after a failed call.
    """
    entry = await _setup_entry(hass)

    zone_id = "test-zone-1"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Test",
        "mode": MODE_TIME_PROGRAM,
        "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    }
    # Capture original program BEFORE the send (Pitfall 6 — must be deep copy reference)
    original = copy.deepcopy(
        entry.runtime_data.runtime_config["zones"][zone_id]["time_program"]
    )

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_time_program",
            "zone_id": zone_id,
            "program": {"mon": []},  # missing 6 day keys
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is False
    # No mutation must have occurred (validate-before-mutate gate)
    assert (
        entry.runtime_data.runtime_config["zones"][zone_id]["time_program"]
        == original
    )


async def test_ws_reset_zone_time_program_default(hass, hass_ws_client):
    """reset_zone_time_program target='default' restores _DEFAULT_DAILY_PROGRAM via deepcopy.

    Verifies ZONE-09 / Pitfall 2: the returned program is a deepcopy — mutating it
    does NOT affect the _DEFAULT_DAILY_PROGRAM module constant.
    """
    entry = await _setup_entry(hass)

    zone_id = "test-zone-1"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Test",
        "mode": MODE_TIME_PROGRAM,
        "time_program": {
            d: [{"start": "00:00", "mode": "comfort"}]
            for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reset_zone_time_program",
            "zone_id": zone_id,
            "target": "default",
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Zone time_program must deep-equal _DEFAULT_DAILY_PROGRAM
    assert (
        entry.runtime_data.runtime_config["zones"][zone_id]["time_program"]
        == _DEFAULT_DAILY_PROGRAM
    )

    # Deepcopy isolation: mutating the assigned program must NOT affect the constant
    entry.runtime_data.runtime_config["zones"][zone_id]["time_program"][
        "mon"
    ].append({"start": "12:00", "mode": "reduced"})
    # Default weekday program has 5 periods
    assert len(_DEFAULT_DAILY_PROGRAM["mon"]) == 5


async def test_ws_reset_zone_time_program_global(hass, hass_ws_client):
    """reset_zone_time_program target='global' copies from default_zone.time_program.

    Phase 14 (D-09): target='global' for a custom zone reads from
    default_zone["time_program"] (the Default Zone's current program).
    Verifies ZONE-09 / Pitfall 2: the copy is independent — mutating the
    zone's program does NOT mutate default_zone.time_program.
    """
    entry = await _setup_entry(hass)

    zone_id = "test-zone-1"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Test",
        "mode": MODE_TIME_PROGRAM,
        "time_program": {
            d: [{"start": "00:00", "mode": "normal"}]
            for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
    }

    # Mutate default_zone.time_program["wed"] to a sentinel BEFORE the WS call
    entry.runtime_data.runtime_config["default_zone"]["time_program"]["wed"] = [
        {"start": "00:00", "mode": "comfort"}
    ]

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reset_zone_time_program",
            "zone_id": zone_id,
            "target": "global",
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Zone's wed must match the sentinel we set on default_zone.time_program
    assert entry.runtime_data.runtime_config["zones"][zone_id]["time_program"][
        "wed"
    ] == [{"start": "00:00", "mode": "comfort"}]

    # Deepcopy isolation: mutating the zone's program must NOT affect
    # default_zone.time_program
    entry.runtime_data.runtime_config["zones"][zone_id]["time_program"][
        "wed"
    ].append({"start": "06:00", "mode": "normal"})
    assert entry.runtime_data.runtime_config["default_zone"]["time_program"][
        "wed"
    ] == [{"start": "00:00", "mode": "comfort"}]


async def test_ws_reset_zone_time_program_default_zone(hass, hass_ws_client):
    """D-09: reset_zone_time_program zone_id="default" target="default" resets
    default_zone.time_program to _DEFAULT_DAILY_PROGRAM.

    Phase 14 (D-09): reset_zone_time_program is extended to handle
    zone_id="default". target="default" deepcopies _DEFAULT_DAILY_PROGRAM into
    default_zone.time_program.
    """
    entry = await _setup_entry(hass)

    # Mutate default_zone.time_program to a stub before sending
    entry.runtime_data.runtime_config["default_zone"]["time_program"] = {
        d: [{"start": "00:00", "mode": "comfort"}]
        for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reset_zone_time_program",
            "zone_id": "default",
            "target": "default",
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Must deep-equal _DEFAULT_DAILY_PROGRAM after reset
    assert (
        entry.runtime_data.runtime_config["default_zone"]["time_program"]
        == _DEFAULT_DAILY_PROGRAM
    )

    # Deepcopy isolation: mutating the result must NOT affect the constant
    entry.runtime_data.runtime_config["default_zone"]["time_program"][
        "mon"
    ].append({"start": "12:00", "mode": "reduced"})
    # Default weekday program has 5 periods
    assert len(_DEFAULT_DAILY_PROGRAM["mon"]) == 5

    # Sentinel invariant: "default" must NOT appear as a key in zones{}
    assert "default" not in entry.runtime_data.runtime_config.get("zones", {})


# ---------------------------------------------------------------------------
# Tests: set_room_config zone_id: null pops the key (CR-03 fix, gap 06-04)
# ---------------------------------------------------------------------------


async def test_set_room_config_pops_zone_id_when_null(hass, hass_ws_client):
    """set_room_config with {zone_id: null} removes the zone_id key from the live room entry.

    Verifies CR-03 fix: the backend handler pops zone_id from the live room entry
    before the sparse-merge so the room becomes a Default Zone member (D-06).
    """
    entry = await _setup_entry(hass)

    # Seed a zone and assign the room to it
    zone_id = "some-uuid"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Test Zone",
        "mode": MODE_TIME_PROGRAM,
        "time_program": {
            d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
    }
    entry.runtime_data.runtime_config.setdefault("rooms", {})["living_room"] = {
        "zone_id": zone_id
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": "living_room",
            "config": {"zone_id": None},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    # zone_id must be absent — room is back in Default Zone (D-06 sparse model)
    living_room = entry.runtime_data.runtime_config["rooms"]["living_room"]
    assert "zone_id" not in living_room


async def test_set_room_config_null_zone_id_is_idempotent_when_already_absent(
    hass, hass_ws_client
):
    """set_room_config with {zone_id: null} on a room with no zone_id is a no-op (idempotent).

    Verifies CR-03 fix: when zone_id is already absent, the pop is a no-op and the
    handler succeeds without error.
    """
    entry = await _setup_entry(hass)

    # Seed a room with no zone_id (already a Default Zone member)
    entry.runtime_data.runtime_config.setdefault("rooms", {})[
        "living_room"
    ] = {}

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": "living_room",
            "config": {"zone_id": None},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    # Room must still equal its original value (no zone_id key added)
    living_room = entry.runtime_data.runtime_config["rooms"]["living_room"]
    assert living_room == {}


async def test_set_room_config_null_zone_id_preserves_other_keys(
    hass, hass_ws_client
):
    """set_room_config with {zone_id: null} pops zone_id but keeps other keys.

    Verifies the pop is targeted — zone_id is correctly absent from the
    resulting room entry (Phase 15 D-07: deprecated keys are silently dropped).
    """
    entry = await _setup_entry(hass)

    entry.runtime_data.runtime_config.setdefault("rooms", {})[
        "living_room"
    ] = {}

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_room_config",
            "room_id": "living_room",
            "config": {"zone_id": None},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    living_room = entry.runtime_data.runtime_config["rooms"]["living_room"]
    # zone_id must NOT be present
    assert "zone_id" not in living_room


# ---------------------------------------------------------------------------
# Gap 1: set_zone_time_program HAPPY PATH (UI-04/ASSIGN-01)
# ---------------------------------------------------------------------------


async def test_ws_set_zone_time_program_accepts_full_program(
    hass, hass_ws_client
):
    """set_zone_time_program with a full 7-day program is accepted and persisted.

    Requirement (Gap 1): A full 7-day zone time program is accepted, persisted to
    runtime_config, and returns success. This is the happy path; the rejection path
    (partial program) is already covered by test_ws_set_zone_time_program_rejects_partial.

    Verifies:
    - result.success is True
    - zone.time_program is updated with the full new program
    - the program persists across runtime_config access (no reference sharing issues)
    """
    entry = await _setup_entry(hass)

    # Seed a custom zone with a default program
    zone_id = "test-zone-uuid-1"
    entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
        "name": "Test Zone",
        "mode": MODE_TIME_PROGRAM,
        "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    }

    # Build a sentinel full 7-day program to send (all days present, even if empty)
    sentinel_program = {
        "mon": [{"start": "06:00", "mode": "normal"}],
        "tue": [{"start": "07:00", "mode": "reduced"}],
        "wed": [{"start": "08:00", "mode": "comfort"}],
        "thu": [{"start": "06:00", "mode": "normal"}],
        "fri": [{"start": "07:00", "mode": "reduced"}],
        "sat": [{"start": "09:00", "mode": "normal"}],
        "sun": [{"start": "10:00", "mode": "normal"}],
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_time_program",
            "zone_id": zone_id,
            "program": sentinel_program,
        }
    )
    msg = await client.receive_json()

    # Happy path: must succeed
    assert msg["success"] is True
    assert msg["result"]["success"] is True

    # Verify persistence: zone.time_program must match the sentinel
    persisted_program = entry.runtime_data.runtime_config["zones"][zone_id][
        "time_program"
    ]
    assert persisted_program == sentinel_program

    # Deep-copy isolation: mutating the sent program must NOT mutate the saved config
    sentinel_program["mon"].append({"start": "12:00", "mode": "comfort"})
    assert entry.runtime_data.runtime_config["zones"][zone_id]["time_program"][
        "mon"
    ] == [{"start": "06:00", "mode": "normal"}], (
        "zone time_program was affected by mutation to the input program — not a deep copy"
    )


# ---------------------------------------------------------------------------
# Tests: set_zone_preheat with zone_id="default" (Phase 14, D-11)
# ---------------------------------------------------------------------------


async def test_ws_set_zone_preheat_default_zone_writes_sub_key(
    hass, hass_ws_client
):
    """D-11: set_zone_preheat zone_id="default" writes default_zone.preheat_enabled.

    Phase 14 (D-11): the "default" sentinel branch must write to
    runtime_config["default_zone"]["preheat_enabled"], not to the old flat
    default_zone_preheat_enabled key.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_preheat",
            "zone_id": "default",
            "enabled": True,
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    # D-11: must write to default_zone sub-dict
    assert (
        entry.runtime_data.runtime_config["default_zone"]["preheat_enabled"]
        is True
    )
    # Old flat key must NOT be created
    assert (
        "default_zone_preheat_enabled" not in entry.runtime_data.runtime_config
    )
    # Sentinel invariant: "default" must NOT appear as a key in zones{}
    assert "default" not in entry.runtime_data.runtime_config.get("zones", {})


# ---------------------------------------------------------------------------
# Tests: even/odd week schedule seeding via set_person_config (Plan 07-02)
# ---------------------------------------------------------------------------


# T-07-W1: single→even_odd seeds both schedule_even and schedule_odd (SCHED-05)
async def test_ws_set_person_config_seeds_even_odd_from_schedule(
    hass, hass_ws_client
):
    """SCHED-05: switching to even_odd seeds schedule_even and schedule_odd
    from the existing schedule when neither key is present in storage.
    """
    entry = await _setup_entry(hass)

    # Seed an existing single schedule for person.alice
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {"schedule": PERSON_SCHEDULE},
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": "person.alice",
            "config": {"schedule_type": "even_odd"},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    assert stored["schedule_type"] == "even_odd"
    assert "schedule_even" in stored
    assert "schedule_odd" in stored
    # Seeded copies must equal the original schedule
    assert stored["schedule_even"] == PERSON_SCHEDULE
    assert stored["schedule_odd"] == PERSON_SCHEDULE
    # Seeded copies must be independent objects (Pitfall 2)
    assert stored["schedule_even"] is not stored["schedule_odd"]


# T-07-W2: seeding guard — second switch does not overwrite existing
#           schedule_even (Pitfall 1)
async def test_ws_set_person_config_does_not_overwrite_existing_schedule_even(
    hass, hass_ws_client
):
    """SCHED-05 guard: schedule_even already in storage → no overwrite."""
    entry = await _setup_entry(hass)

    custom_even = {
        "mon": [{"start": "06:00", "state": "present"}],
        **{d: [] for d in ["tue", "wed", "thu", "fri", "sat", "sun"]},
    }
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {
            "schedule_type": "even_odd",
            "schedule_even": custom_even,
            "schedule_odd": {},
        }
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": "person.alice",
            "config": {"schedule_type": "even_odd"},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    # schedule_even must remain the custom value (not reset)
    assert stored["schedule_even"] == custom_even


# T-07-W3: set_person_config with schedule_type="single" does not touch
#           schedule_even / schedule_odd (D-02)
async def test_ws_set_person_config_single_does_not_seed(hass, hass_ws_client):
    """D-02: schedule_type=single → no seeding, schedule_even/odd not added."""
    entry = await _setup_entry(hass)
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {"schedule": PERSON_SCHEDULE},
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": "person.alice",
            "config": {"schedule_type": "single"},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    assert "schedule_even" not in stored
    assert "schedule_odd" not in stored


# T-07-W4: after even_odd→single revert, schedule_even/odd preserved (SCHED-06)
async def test_ws_set_person_config_revert_preserves_week_schedules(
    hass, hass_ws_client
):
    """D-02: reverting to single preserves schedule_even and schedule_odd."""
    entry = await _setup_entry(hass)

    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {
            "schedule_type": "even_odd",
            "schedule_even": PERSON_SCHEDULE,
            "schedule_odd": PERSON_SCHEDULE,
        }
    }

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": "person.alice",
            "config": {"schedule_type": "single"},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    assert stored["schedule_type"] == "single"
    # D-02: week schedules silently preserved — user can switch back later
    assert "schedule_even" in stored
    assert "schedule_odd" in stored


# ---------------------------------------------------------------------------
# Tests: set_calibration_config WS command (Plan 09-03, CALIB-01)
# ---------------------------------------------------------------------------


async def test_ws_set_calibration_config_enabled_true(hass, hass_ws_client):
    """set_calibration_config {enabled: true} persists calibration_enabled=True.

    Verifies CALIB-01 happy path:
    - WS result is success
    - runtime_config["calibration_enabled"] is True after the call
    - No async_evaluate triggered (Pitfall 4: calibration config is not a
      mode change — it takes effect on the next scheduled cycle).
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_calibration_config", "enabled": True}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    assert entry.runtime_data.runtime_config["calibration_enabled"] is True


async def test_ws_set_calibration_config_enabled_false(hass, hass_ws_client):
    """set_calibration_config {enabled: false} persists calibration_enabled=False.

    Verifies CALIB-01 disable path:
    - WS result is success
    - runtime_config["calibration_enabled"] is False after the call
    """
    entry = await _setup_entry(hass)

    # Pre-seed calibration_enabled=True to confirm the command can flip it
    entry.runtime_data.runtime_config["calibration_enabled"] = True

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_calibration_config", "enabled": False}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    assert entry.runtime_data.runtime_config["calibration_enabled"] is False


# ---------------------------------------------------------------------------
# Tests: set_matter_mapping WS command (Plan 13-02, MCALIB-01/02)
# ---------------------------------------------------------------------------


async def test_set_matter_mapping_stores_mapping(hass, hass_ws_client):
    """set_matter_mapping stores the mapping in matter_mappings[tado_entity_id].

    Verifies D-15: valid {tado_entity_id, matter_entity_ids} payload is
    persisted under runtime_config["matter_mappings"].
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_matter_mapping",
            "tado_entity_id": "climate.tado_lr",
            "matter_entity_ids": [
                "climate.valve1",
                "climate.valve2",
            ],
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    mappings = entry.runtime_data.runtime_config.get("matter_mappings", {})
    assert mappings.get("climate.tado_lr") == [
        "climate.valve1",
        "climate.valve2",
    ]


async def test_set_matter_mapping_empty_list_pops_key(hass, hass_ws_client):
    """set_matter_mapping with matter_entity_ids=[] removes the key (sparse).

    Verifies D-01: empty list must pop the tado_entity_id key — the mapping
    is never stored as []. Sparse model: absent key = no mapping.
    """
    entry = await _setup_entry(hass)

    # Pre-seed an existing mapping
    entry.runtime_data.runtime_config.setdefault("matter_mappings", {})[
        "climate.tado_lr"
    ] = ["climate.valve1"]

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_matter_mapping",
            "tado_entity_id": "climate.tado_lr",
            "matter_entity_ids": [],
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    mappings = entry.runtime_data.runtime_config.get("matter_mappings", {})
    # Key must be absent (sparse — never stored as [])
    assert "climate.tado_lr" not in mappings


async def test_set_matter_mapping_filters_non_climate_entity_ids(
    hass, hass_ws_client
):
    """set_matter_mapping filters out non-climate.* entity IDs (Pitfall 7).

    Verifies T-13-04: a payload with mixed entity_ids stores only the
    climate.* entries; sensor.* and other domains are silently dropped.
    """
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_matter_mapping",
            "tado_entity_id": "climate.tado_lr",
            "matter_entity_ids": [
                "sensor.foo",
                "climate.valve1",
            ],
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    mappings = entry.runtime_data.runtime_config.get("matter_mappings", {})
    # Only the climate.* entity must be stored
    assert mappings.get("climate.tado_lr") == ["climate.valve1"]


async def test_set_matter_mapping_triggers_listener_refresh(
    hass, hass_ws_client
):
    """set_matter_mapping triggers coordinator._async_refresh_matter_listeners.

    Verifies D-16: after persisting, the coordinator's Matter listeners are
    refreshed atomically. Uses a monkeypatch spy on the coordinator method;
    allows for hass.async_create_task scheduling via
    hass.async_block_till_done().
    """
    entry = await _setup_entry(hass)
    coordinator = entry.runtime_data.coordinator

    refresh_called = []

    async def _spy_refresh():
        refresh_called.append(True)

    coordinator._async_refresh_matter_listeners = _spy_refresh

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_matter_mapping",
            "tado_entity_id": "climate.tado_lr",
            "matter_entity_ids": ["climate.valve1"],
        }
    )
    msg = await client.receive_json()
    await hass.async_block_till_done()

    assert msg["success"] is True
    assert len(refresh_called) == 1, (
        "_async_refresh_matter_listeners must be called once"
    )


# ---------------------------------------------------------------------------
# Test: suggest_matter_mappings WS command (Plan quick/260603-o8e)
# ---------------------------------------------------------------------------


async def test_ws_suggest_matter_mappings_returns_mappings(
    hass, hass_ws_client
):
    """suggest_matter_mappings returns {"mappings": {}} on a fresh hass
    with no Tado X or Matter entities.

    Verifies the command is registered, returns success=True, and the
    result contains a "mappings" key that is a dict.
    """
    await _setup_entry(hass)
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/suggest_matter_mappings"}
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    assert "mappings" in msg["result"]
    assert isinstance(msg["result"]["mappings"], dict)

"""Tests for ClimateManagerStore (sparse-merge Store layer).

TDD RED phase: these tests are written before storage.py exists.
All four behaviors verified per plan 02 Task 1.
"""
import copy
import pytest

from custom_components.climate_manager.const import DEFAULT_CONFIG
from custom_components.climate_manager.storage import ClimateManagerStore, validate_zone_assignment


async def test_load_fresh_install_returns_default_config(hass):
    """Test 1: async_load() on fresh install returns DEFAULT_CONFIG (as a deep copy)."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()

    assert result == DEFAULT_CONFIG


async def test_load_fresh_install_returns_copy_not_same_object(hass):
    """Test 1b: Mutating the returned dict must NOT mutate DEFAULT_CONFIG."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()

    # Mutate the returned config
    result["global_mode"] = "off"
    result["rooms"]["new_room"] = {
        "time_program": {d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}
    }

    # DEFAULT_CONFIG must be unchanged
    assert DEFAULT_CONFIG["global_mode"] == "time_program"
    assert "new_room" not in DEFAULT_CONFIG["rooms"]


async def test_load_sparse_stored_data_merges_over_defaults(hass):
    """Test 2: async_load() with sparse stored data merges override over defaults."""
    store = ClimateManagerStore(hass)

    # Manually write sparse data to the underlying store
    await store._store.async_save({"global_mode": "off"})

    result = await store.async_load()

    # Stored override wins
    assert result["global_mode"] == "off"
    # Defaults still present for unset keys
    assert result["period_temperatures"] == DEFAULT_CONFIG["period_temperatures"]
    assert result["global_time_program"] == DEFAULT_CONFIG["global_time_program"]
    assert result["rooms"] == DEFAULT_CONFIG["rooms"]
    assert result["persons"] == DEFAULT_CONFIG["persons"]


async def test_save_then_load_round_trips(hass):
    """Test 3: async_save(config) followed by async_load() round-trips the saved config."""
    store = ClimateManagerStore(hass)

    config_to_save = copy.deepcopy(DEFAULT_CONFIG)
    config_to_save["global_mode"] = "off"
    config_to_save["period_temperatures"]["comfort"] = 24.0

    await store.async_save(config_to_save)
    loaded = await store.async_load()

    assert loaded["global_mode"] == "off"
    assert loaded["period_temperatures"]["comfort"] == 24.0


async def test_load_room_override_survives(hass):
    """Test 4: A stored room override survives load and appears under rooms[area_id]."""
    store = ClimateManagerStore(hass)

    _DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    room_time_program = {d: [] for d in _DAYS}

    config_with_room = copy.deepcopy(DEFAULT_CONFIG)
    config_with_room["rooms"]["living_room"] = {
        "time_program": room_time_program
    }

    await store.async_save(config_with_room)
    loaded = await store.async_load()

    assert "living_room" in loaded["rooms"]
    assert loaded["rooms"]["living_room"] == {
        "time_program": room_time_program
    }


# ---------------------------------------------------------------------------
# D-21 migration tests: present → force_present, absent → force_absent
# ---------------------------------------------------------------------------


async def test_load_migrates_present_to_force_present(hass):
    """D-21 migration: stored person mode 'present' is renamed to 'force_present' on load."""
    store = ClimateManagerStore(hass)
    await store._store.async_save({"persons": {"person.a": {"mode": "present"}}})
    result = await store.async_load()
    assert result["persons"]["person.a"]["mode"] == "force_present"


async def test_load_migrates_absent_to_force_absent(hass):
    """D-21 migration: stored person mode 'absent' is renamed to 'force_absent' on load."""
    store = ClimateManagerStore(hass)
    await store._store.async_save({"persons": {"person.a": {"mode": "absent"}}})
    result = await store.async_load()
    assert result["persons"]["person.a"]["mode"] == "force_absent"


async def test_load_already_migrated_force_present_unchanged(hass):
    """D-21 migration idempotency: 'force_present' mode is not modified on re-load."""
    store = ClimateManagerStore(hass)
    await store._store.async_save({"persons": {"person.a": {"mode": "force_present"}}})
    result = await store.async_load()
    assert result["persons"]["person.a"]["mode"] == "force_present"


async def test_load_unrelated_modes_unchanged(hass):
    """D-21 migration: 'scheduled' and 'ha' modes are not affected by the migration."""
    store = ClimateManagerStore(hass)
    await store._store.async_save({
        "persons": {
            "person.sched": {"mode": "scheduled"},
            "person.ha": {"mode": "ha"},
        }
    })
    result = await store.async_load()
    assert result["persons"]["person.sched"]["mode"] == "scheduled"
    assert result["persons"]["person.ha"]["mode"] == "ha"


# ---------------------------------------------------------------------------
# Phase 4 zone schema tests (ZONE-01, ZONE-02, ZONE-03, ZONE-04)
# ---------------------------------------------------------------------------


async def test_load_fresh_install_includes_zones_and_default_zone_name(hass):
    """Fresh install returns DEFAULT_CONFIG with zones:{} and default_zone_name present."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()
    assert "zones" in result
    assert result["zones"] == {}
    assert "default_zone_name" in result
    assert result["default_zone_name"] == "Home"


async def test_load_v10_data_without_zones_gets_defaults(hass):
    """v1.0 stored data without zones/default_zone_name loads cleanly (D-04, ZONE-03)."""
    store = ClimateManagerStore(hass)
    # Simulate v1.0 stored data — no zones, no default_zone_name
    # Use _store (underlying HA Store) directly to bypass validation and write raw bytes
    await store._store.async_save({"global_mode": "off"})
    result = await store.async_load()
    assert result["zones"] == {}
    assert result["default_zone_name"] == "Home"
    assert result["global_mode"] == "off"  # stored value survives


async def test_save_then_load_round_trips_zone(hass):
    """A saved zone survives load and appears under zones[uuid] (ZONE-01)."""
    store = ClimateManagerStore(hass)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["zones"]["test-uuid"] = {
        "name": "Test Zone",
        "mode": "time_program",
        "time_program": {d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
    }
    await store.async_save(config)
    loaded = await store.async_load()
    assert "test-uuid" in loaded["zones"]
    assert loaded["zones"]["test-uuid"]["name"] == "Test Zone"
    assert loaded["zones"]["test-uuid"]["mode"] == "time_program"
    assert loaded["zones"]["test-uuid"]["time_program"] == {
        d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }


def test_validate_zone_assignment_valid_config_passes():
    """validate_zone_assignment raises nothing for a valid config."""
    config = {
        "zones": {"uuid-1": {"name": "Zone A", "mode": "time_program", "time_program": {}}},
        "rooms": {"living_room": {"zone_id": "uuid-1", "room_mode": "global"}},
    }
    validate_zone_assignment(config)  # must not raise


def test_validate_zone_assignment_unknown_zone_id_raises():
    """validate_zone_assignment raises ValueError for unknown zone_id (referential integrity)."""
    config = {
        "zones": {},
        "rooms": {"living_room": {"zone_id": "nonexistent-uuid"}},
    }
    with pytest.raises(ValueError, match="unknown zone_id"):
        validate_zone_assignment(config)


def test_validate_zone_assignment_default_zone_rooms_pass():
    """Rooms without zone_id (Default Zone members) pass validation (D-06)."""
    config = {
        "zones": {},
        "rooms": {"bedroom": {"room_mode": "custom"}},  # no zone_id
    }
    validate_zone_assignment(config)  # must not raise


def test_validate_zone_assignment_multiple_rooms_same_zone_accepted():
    """validate_zone_assignment accepts multiple rooms sharing the same zone_id (ZONE-04: rooms belong to at most one zone, zones can contain many rooms)."""
    config = {
        "zones": {"uuid-1": {"name": "Zone A", "mode": "time_program", "time_program": {}}},
        "rooms": {
            "living_room": {"zone_id": "uuid-1"},
            "bedroom": {"zone_id": "uuid-1"},
        },
    }
    validate_zone_assignment(config)  # must not raise


async def test_save_rejects_unknown_zone_id(hass):
    """async_save raises ValueError when a room references a non-existent zone_id (ZONE-04)."""
    store = ClimateManagerStore(hass)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rooms"]["living_room"] = {"zone_id": "ghost-uuid"}
    # zones is {} (default) so ghost-uuid is not defined — must raise
    with pytest.raises(ValueError, match="unknown zone_id"):
        await store.async_save(config)


async def test_save_accepts_room_without_zone_id(hass):
    """async_save succeeds when a room has no zone_id (Default Zone member — D-06)."""
    store = ClimateManagerStore(hass)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rooms"]["bedroom"] = {"room_mode": "global"}  # no zone_id
    await store.async_save(config)
    loaded = await store.async_load()
    assert "bedroom" in loaded["rooms"]
    assert "zone_id" not in loaded["rooms"]["bedroom"]

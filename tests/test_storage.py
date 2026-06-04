"""Tests for ClimateManagerStore (sparse-merge Store layer).

TDD RED phase: these tests are written before storage.py exists.
All four behaviors verified per plan 02 Task 1.
"""

import copy
import pytest

from custom_components.climate_manager.const import DEFAULT_CONFIG
from custom_components.climate_manager.storage import (
    ClimateManagerStore,
    validate_zone_assignment,
)


async def test_load_fresh_install_returns_default_config(hass):
    """Test 1: async_load() on fresh install returns DEFAULT_CONFIG (as a deep copy)."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()

    assert result == DEFAULT_CONFIG


async def test_load_fresh_install_returns_copy_not_same_object(hass):
    """Test 1b: Mutating the returned dict must NOT mutate DEFAULT_CONFIG."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()

    # Mutate the returned config (Phase 14: mutate default_zone.mode)
    result["default_zone"]["mode"] = "off"
    result["rooms"]["new_room"] = {
        "time_program": {
            d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        }
    }

    # DEFAULT_CONFIG must be unchanged
    assert DEFAULT_CONFIG["default_zone"]["mode"] == "time_program"
    assert "new_room" not in DEFAULT_CONFIG["rooms"]


async def test_load_sparse_stored_data_merges_over_defaults(hass):
    """Test 2: async_load() with sparse stored data merges override over defaults.

    Phase 14: legacy format with global_mode triggers compat shim.
    """
    store = ClimateManagerStore(hass)

    # Manually write sparse data to the underlying store (old format)
    await store._store.async_save({"global_mode": "off"})

    result = await store.async_load()

    # Compat shim promotes global_mode → default_zone["mode"]
    assert result["default_zone"]["mode"] == "off"
    assert "global_mode" not in result
    # Defaults still present for unset keys
    assert (
        result["period_temperatures"] == DEFAULT_CONFIG["period_temperatures"]
    )
    assert result["rooms"] == DEFAULT_CONFIG["rooms"]
    assert result["persons"] == DEFAULT_CONFIG["persons"]


async def test_save_then_load_round_trips(hass):
    """Test 3: async_save(config) followed by async_load() round-trips the saved config.

    Phase 14: mutates default_zone.mode instead of the removed global_mode key.
    """
    store = ClimateManagerStore(hass)

    config_to_save = copy.deepcopy(DEFAULT_CONFIG)
    config_to_save["default_zone"]["mode"] = "off"
    config_to_save["period_temperatures"]["comfort"] = 24.0

    await store.async_save(config_to_save)
    loaded = await store.async_load()

    assert loaded["default_zone"]["mode"] == "off"
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
    assert loaded["rooms"]["living_room"] == {"time_program": room_time_program}


# ---------------------------------------------------------------------------
# D-21 migration tests: present → force_present, absent → force_absent
# ---------------------------------------------------------------------------


async def test_load_migrates_present_to_force_present(hass):
    """D-21 migration: stored person mode 'present' is renamed to 'force_present' on load."""
    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {"persons": {"person.a": {"mode": "present"}}}
    )
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
    await store._store.async_save(
        {"persons": {"person.a": {"mode": "force_present"}}}
    )
    result = await store.async_load()
    assert result["persons"]["person.a"]["mode"] == "force_present"


async def test_load_unrelated_modes_unchanged(hass):
    """D-21 migration: 'scheduled' and 'ha' modes are not affected by the migration."""
    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.sched": {"mode": "scheduled"},
                "person.ha": {"mode": "ha"},
            }
        }
    )
    result = await store.async_load()
    assert result["persons"]["person.sched"]["mode"] == "scheduled"
    assert result["persons"]["person.ha"]["mode"] == "ha"


# ---------------------------------------------------------------------------
# Phase 4 zone schema tests (ZONE-01, ZONE-02, ZONE-03, ZONE-04)
# ---------------------------------------------------------------------------


async def test_load_fresh_install_includes_zones_and_default_zone_name(hass):
    """Fresh install returns DEFAULT_CONFIG with zones:{} and default_zone present."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()
    assert "zones" in result
    assert result["zones"] == {}
    assert "default_zone" in result
    assert result["default_zone"]["name"] == "Home"
    assert result["default_zone"]["mode"] == "time_program"


async def test_load_v10_data_without_zones_gets_defaults(hass):
    """v1.0 stored data without zones/default_zone loads cleanly (D-04, ZONE-03).

    Phase 14: compat shim promotes global_mode to default_zone.
    """
    store = ClimateManagerStore(hass)
    # Simulate v1.0 stored data — no zones, no default_zone
    # Use _store (underlying HA Store) directly to bypass validation and write raw bytes
    await store._store.async_save({"global_mode": "off"})
    result = await store.async_load()
    assert result["zones"] == {}
    assert result["default_zone"]["mode"] == "off"
    assert "global_mode" not in result


async def test_save_then_load_round_trips_zone(hass):
    """A saved zone survives load and appears under zones[uuid] (ZONE-01)."""
    store = ClimateManagerStore(hass)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["zones"]["test-uuid"] = {
        "name": "Test Zone",
        "mode": "time_program",
        "time_program": {
            d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
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
        "zones": {
            "uuid-1": {
                "name": "Zone A",
                "mode": "time_program",
                "time_program": {},
            }
        },
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
        "zones": {
            "uuid-1": {
                "name": "Zone A",
                "mode": "time_program",
                "time_program": {},
            }
        },
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


# ---------------------------------------------------------------------------
# Test: validate_zone_assignment defense-in-depth — rejects stored null zone_id
# ---------------------------------------------------------------------------


def test_validate_zone_assignment_rejects_explicit_null():
    """validate_zone_assignment raises ValueError for stored zone_id: null (D-06 defense in depth).

    The storage layer must never accept a room with zone_id: None stored on disk.
    The ws_set_room_config handler pops the key before save (CR-03 fix), so this
    validator should never see null in the happy path — but if a future bug bypasses
    the handler, the validator acts as the last line of defense.
    """
    config = {"zones": {}, "rooms": {"living_room": {"zone_id": None}}}
    with pytest.raises(
        ValueError, match="sparse model prohibits explicit null"
    ):
        validate_zone_assignment(config)


# ---------------------------------------------------------------------------
# Phase 14 compat shim tests (D-02, D-03)
# ---------------------------------------------------------------------------

_ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


async def test_load_legacy_flat_keys_builds_default_zone(hass):
    """Phase 14 compat shim: old format with global_mode is promoted to default_zone."""
    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "global_mode": "off",
            "global_time_program": {d: [] for d in _ALL_DAYS},
            "default_zone_name": "Maison",
            "default_zone_preheat_enabled": True,
        }
    )
    result = await store.async_load()
    assert result["default_zone"]["mode"] == "off"
    assert result["default_zone"]["name"] == "Maison"
    assert result["default_zone"]["preheat_enabled"] is True
    assert "global_mode" not in result
    assert "global_time_program" not in result
    assert "default_zone_name" not in result
    # Day-fill: empty day lists are filled with defaults before absorption
    for day in _ALL_DAYS:
        assert result["default_zone"]["time_program"][day] != []


async def test_load_new_format_reads_default_zone_directly(hass):
    """Phase 14: new format with default_zone key loads without shim."""
    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "default_zone": {
                "name": "Home",
                "mode": "time_program",
                "time_program": {d: [] for d in _ALL_DAYS},
                "preheat_enabled": False,
            }
        }
    )
    result = await store.async_load()
    assert result["default_zone"]["mode"] == "time_program"
    assert "global_mode" not in result
    # Day-fill: empty day lists in new-format default_zone.time_program are filled
    for day in _ALL_DAYS:
        assert result["default_zone"]["time_program"][day] != []


# ---------------------------------------------------------------------------
# Phase 15 compat shim tests (D-01, D-02, D-03)
# ---------------------------------------------------------------------------


async def test_load_strips_room_mode_from_room_records(hass):
    """Phase 15 compat shim: room_mode and time_program are stripped from rooms.

    Stores data with room records containing room_mode and time_program keys.
    After async_load(), both keys must be absent from all room records.
    Zone time programs must be unaffected (Pitfall 2 guard).
    """
    store = ClimateManagerStore(hass)
    sentinel_zone_program = {
        d: [{"start": "06:00", "mode": "normal"}] for d in _ALL_DAYS
    }
    await store._store.async_save(
        {
            "rooms": {
                "room-a": {
                    "room_mode": "custom",
                    "time_program": sentinel_zone_program,
                    "zone_id": "uuid-1",
                },
                "room-b": {
                    "room_mode": "frost_protection",
                },
                "room-c": {
                    "zone_id": "uuid-1",
                    # no room_mode — should load unchanged
                },
            },
            "zones": {
                "uuid-1": {
                    "name": "Test zone",
                    "mode": "time_program",
                    "time_program": sentinel_zone_program,
                    "preheat_enabled": False,
                }
            },
        }
    )
    result = await store.async_load()

    # room_mode and time_program absent from all room records
    for room_id, room_cfg in result["rooms"].items():
        assert "room_mode" not in room_cfg, (
            f"room_mode still present in {room_id}"
        )
        assert "time_program" not in room_cfg, (
            f"time_program still present in {room_id}"
        )
    # zone time_program is untouched (Pitfall 2)
    assert result["zones"]["uuid-1"]["time_program"] == sentinel_zone_program
    # zone_id on room-a and room-c survives (only room_mode/time_program stripped)
    assert result["rooms"]["room-a"]["zone_id"] == "uuid-1"
    assert result["rooms"]["room-c"]["zone_id"] == "uuid-1"

"""Tests for ClimateManagerStore (sparse-merge Store layer).

TDD RED phase: these tests are written before storage.py exists.
All four behaviors verified per plan 02 Task 1.
"""
import copy
import pytest

from custom_components.climate_manager.const import DEFAULT_CONFIG
from custom_components.climate_manager.storage import ClimateManagerStore


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
    result["rooms"]["new_room"] = {"time_program": {"weekday_groups": []}}

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

    config_with_room = copy.deepcopy(DEFAULT_CONFIG)
    config_with_room["rooms"]["living_room"] = {
        "time_program": {"weekday_groups": []}
    }

    await store.async_save(config_with_room)
    loaded = await store.async_load()

    assert "living_room" in loaded["rooms"]
    assert loaded["rooms"]["living_room"] == {
        "time_program": {"weekday_groups": []}
    }

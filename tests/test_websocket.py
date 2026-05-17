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
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
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

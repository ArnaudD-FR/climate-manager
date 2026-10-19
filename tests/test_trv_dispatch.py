"""Tests for setpoint dispatch: concurrency, timeouts and resynchronisation.

Tests:
- All valves receive their command at the same time (zones/rooms gathered)
- An unresponsive valve times out without stalling the others
- Only one evaluation runs at a time; requests are coalesced, never lost
- The manual-override hold is lifted on period change
- push | / hold | INFO logs
- A valve coming back online gets its setpoint re-applied immediately
- Startup push is forced, and reaches valves that appear after setup
"""

import asyncio
import logging
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_TIME_PROGRAM,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
)

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

ALL_DAYS_NORMAL_PROGRAM: dict = {
    day: [{"start": "00:00", "mode": PERIOD_NORMAL}] for day in _DAYS
}

# Reduced until 07:00, then Normal.
MORNING_PROGRAM: dict = {
    day: [
        {"start": "00:00", "mode": PERIOD_REDUCED},
        {"start": "07:00", "mode": PERIOD_NORMAL},
    ]
    for day in _DAYS
}

NORMAL = DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
REDUCED = DEFAULT_PERIOD_TEMPERATURES[PERIOD_REDUCED]

TRV_A = "climate.a_trv"
TRV_B = "climate.b_trv"

# Monday 2026-01-05 in the US/Pacific test harness timezone.
BEFORE_7 = "2026-01-05 14:59:00"  # 06:59 local → Reduced
AFTER_7 = "2026-01-05 15:00:30"  # 07:00 local → Normal


def _config(program: dict, two_zones: bool = False) -> dict:
    """Build a runtime_config; room "b" goes to a second zone if asked."""
    zones = {}
    rooms = {}
    if two_zones:
        zones = {
            "z2": {
                "name": "Second",
                "mode": MODE_TIME_PROGRAM,
                "time_program": program,
                "preheat_enabled": False,
            }
        }
        rooms = {"b": {"zone_id": "z2"}}
    return {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": MODE_TIME_PROGRAM,
            "time_program": program,
            "preheat_enabled": False,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": rooms,
        "persons": {},
        "zones": zones,
    }


async def _setup(hass, program: dict, rooms: dict, two_zones: bool = False):
    """Set up the integration, then install the test rooms and config."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entry.runtime_data.runtime_config = _config(program, two_zones)
    entry.runtime_data.rooms = rooms
    return entry, entry.runtime_data.coordinator


def _calls_for(calls, entity_id: str) -> list:
    return [c for c in calls if c.data.get("entity_id") == entity_id]


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time(AFTER_7)
async def test_all_valves_pushed_concurrently(hass):
    """Valve B (other room, other zone) is served while valve A blocks."""
    hass.states.async_set(TRV_A, "heat", {"temperature": 15.0})
    hass.states.async_set(TRV_B, "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")

    release_a = asyncio.Event()
    b_called = asyncio.Event()

    async def _set_temperature(call):
        if call.data["entity_id"] == TRV_A:
            await release_a.wait()
        else:
            b_called.set()

    hass.services.async_register("climate", "set_temperature", _set_temperature)

    _, coordinator = await _setup(
        hass, ALL_DAYS_NORMAL_PROGRAM, {"a": [TRV_A], "b": [TRV_B]}, True
    )

    task = hass.async_create_task(coordinator.async_evaluate())
    await asyncio.wait_for(b_called.wait(), timeout=1)
    assert not task.done(), "A still blocked while B was already served"

    release_a.set()
    await task


async def test_unresponsive_valve_times_out(hass, caplog):
    """A valve that never answers times out; B is served; A is retried.

    No freeze_time here: it also freezes the event loop clock, so the
    timeout would never expire. The all-Normal program is time-independent.
    """
    hass.states.async_set(TRV_A, "heat", {"temperature": 15.0})
    hass.states.async_set(TRV_B, "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")

    calls: list[str] = []
    a_responds = False

    async def _set_temperature(call):
        calls.append(call.data["entity_id"])
        if call.data["entity_id"] == TRV_A and not a_responds:
            await asyncio.Event().wait()  # never answers

    hass.services.async_register("climate", "set_temperature", _set_temperature)

    _, coordinator = await _setup(
        hass, ALL_DAYS_NORMAL_PROGRAM, {"a": [TRV_A], "b": [TRV_B]}
    )

    with patch(
        "custom_components.climate_manager.trv.TRV_COMMAND_TIMEOUT", 0.05
    ):
        await asyncio.wait_for(coordinator.async_evaluate(), timeout=2)
        assert TRV_A in calls and TRV_B in calls
        assert any("timeout | trv=climate.a_trv" in m for m in caplog.messages)
        assert coordinator._get_trv(TRV_A).last_pushed is None

        # Next cycle: A answers now and is retried; B is not re-pushed.
        a_responds = True
        calls.clear()
        await asyncio.wait_for(coordinator.async_evaluate(), timeout=2)
        assert calls == [TRV_A]
        assert coordinator._get_trv(TRV_A).last_pushed == NORMAL


@pytest.mark.freeze_time(AFTER_7)
async def test_evaluations_are_serialised_and_coalesced(hass):
    """A 2nd/3rd evaluate during a stalled run returns at once; one catch-up."""
    entry, coordinator = await _setup(hass, ALL_DAYS_NORMAL_PROGRAM, {})

    runs = 0
    release = asyncio.Event()
    started = asyncio.Event()

    async def _slow_once():
        nonlocal runs
        runs += 1
        started.set()
        if runs == 1:
            await release.wait()

    with patch.object(coordinator, "_async_evaluate_once", _slow_once):
        first = hass.async_create_task(coordinator.async_evaluate())
        await started.wait()

        # Both return immediately while the first run is stalled.
        await asyncio.wait_for(coordinator.async_evaluate(), timeout=0.5)
        await asyncio.wait_for(coordinator.async_evaluate(), timeout=0.5)
        assert runs == 1

        release.set()
        await first

    assert runs == 2, "exactly one catch-up run"


# ---------------------------------------------------------------------------
# Manual-override hold
# ---------------------------------------------------------------------------


async def test_hold_lifted_on_period_change(hass, freezer, caplog):
    """A valve changed outside Climate Manager is re-driven at the next period.

    Reproduces the incident: the valve was set to 18 °C by the Tado app
    while Climate Manager had pushed something else; at 07:00 the Normal
    setpoint must reach it anyway.
    """
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(BEFORE_7)
    hass.states.async_set(TRV_A, "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")

    _, coordinator = await _setup(hass, MORNING_PROGRAM, {"a": [TRV_A]})

    await coordinator.async_evaluate()
    assert _calls_for(calls, TRV_A)[-1].data["temperature"] == REDUCED
    hass.states.async_set(TRV_A, "heat", {"temperature": REDUCED})

    # Changed outside Climate Manager: same period → hold, logged once.
    hass.states.async_set(TRV_A, "heat", {"temperature": 17.0})
    before = len(calls)
    await coordinator.async_evaluate()
    await coordinator.async_evaluate()
    assert len(calls) == before
    holds = [m for m in caplog.messages if m.startswith("hold | trv=a_trv")]
    assert len(holds) == 1

    # Period change → hold lifted, Normal pushed.
    freezer.move_to(AFTER_7)
    await coordinator.async_evaluate()
    assert _calls_for(calls, TRV_A)[-1].data["temperature"] == NORMAL
    assert any(
        r.levelno == logging.INFO
        and r.message.startswith("push | room=a trv=a_trv temp=20.0°C")
        and "slot=normal" in r.message
        for r in caplog.records
    )


# ---------------------------------------------------------------------------
# Back online / startup
# ---------------------------------------------------------------------------


async def test_back_online_reapplies_setpoint(hass, freezer, caplog):
    """Valve offline at the period change gets its setpoint when back."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(BEFORE_7)
    hass.states.async_set(TRV_A, "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")

    _, coordinator = await _setup(hass, MORNING_PROGRAM, {"a": [TRV_A]})
    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    hass.states.async_set(TRV_A, "heat", {"temperature": REDUCED})
    await hass.async_block_till_done()

    # Offline across the period change → nothing sent.
    hass.states.async_set(TRV_A, "unavailable", {})
    await hass.async_block_till_done()
    freezer.move_to(AFTER_7)
    before = len(calls)
    await coordinator.async_evaluate()
    assert len(calls) == before

    # Back online with its own setpoint → evaluation triggered at once.
    hass.states.async_set(TRV_A, "heat", {"temperature": 16.0})
    await hass.async_block_till_done()
    assert _calls_for(calls, TRV_A)[-1].data["temperature"] == NORMAL
    assert any("online | trv=a_trv" in m for m in caplog.messages)


@pytest.mark.freeze_time(AFTER_7)
async def test_startup_push_is_forced_once(hass):
    """First push is sent even if the valve already shows the setpoint."""
    hass.states.async_set(TRV_A, "heat", {"temperature": NORMAL})
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")

    _, coordinator = await _setup(hass, ALL_DAYS_NORMAL_PROGRAM, {"a": [TRV_A]})
    await coordinator.async_evaluate()
    assert len(_calls_for(calls, TRV_A)) == 1

    await coordinator.async_evaluate()
    assert len(_calls_for(calls, TRV_A)) == 1, "no re-push afterwards"


@pytest.mark.freeze_time(AFTER_7)
async def test_valve_appearing_after_startup_gets_setpoint(hass):
    """A valve with no state at setup is pushed as soon as it appears."""
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")

    _, coordinator = await _setup(hass, ALL_DAYS_NORMAL_PROGRAM, {"a": [TRV_A]})
    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    assert _calls_for(calls, TRV_A) == []

    # Integration finishes loading: the entity gets its first state.
    hass.states.async_set(TRV_A, "heat", {"temperature": NORMAL})
    await hass.async_block_till_done()
    assert len(_calls_for(calls, TRV_A)) == 1
    assert _calls_for(calls, TRV_A)[0].data["temperature"] == NORMAL


@pytest.mark.freeze_time(AFTER_7)
async def test_config_rebuild_keeps_push_state(hass):
    """A config edit (domain rebuild) does not re-force every valve."""
    hass.states.async_set(TRV_A, "heat", {"temperature": 15.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")

    entry, coordinator = await _setup(
        hass, ALL_DAYS_NORMAL_PROGRAM, {"a": [TRV_A]}
    )
    await coordinator.async_evaluate()
    hass.states.async_set(TRV_A, "heat", {"temperature": NORMAL})
    assert len(_calls_for(calls, TRV_A)) == 1

    entry.runtime_data.runtime_config["default_zone"]["name"] = "Renamed"
    await coordinator.async_evaluate()
    assert len(_calls_for(calls, TRV_A)) == 1

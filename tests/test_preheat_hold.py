"""Multi-cycle pre-heat tests through the coordinator.

Tests:
- The pre-heat setpoint is held on every tick until the occupied time
  (the zone schedule no longer undoes it one minute later)
- The room period sensor reports "preheat" while it holds
- Convergence records a lead-time sample but keeps holding until the
  occupied time
- The room temperature sensor (not the TRV) decides convergence / warmth
- No pre-heat in a zone that is off
- A config rebuild keeps a running pre-heat
"""

import logging

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    PERIOD_NORMAL,
    PERIOD_PREHEAT,
    PERIOD_REDUCED,
)

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

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

TRV = "climate.a_trv"
SENSOR = "sensor.a_temperature"


def _utc(local_hhmm: str) -> str:
    """Monday 2026-01-05 local (US/Pacific test TZ, UTC-8) → UTC string."""
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    return f"2026-01-05 {hh + 8:02d}:{mm:02d}:00"


def _config(zone_mode: str = MODE_TIME_PROGRAM, rooms: dict | None = None):
    return {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": zone_mode,
            "time_program": MORNING_PROGRAM,
            "preheat_enabled": True,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": rooms or {},
        "persons": {},
        "zones": {},
    }


async def _setup(hass, config: dict):
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entry.runtime_data.runtime_config = config
    entry.runtime_data.rooms = {"a": [TRV]}
    return entry, entry.runtime_data.coordinator, calls


async def _tick(hass, freezer, coordinator, calls, local: str, room_temp):
    """Run one evaluation at `local`; the TRV then reports what it got."""
    freezer.move_to(_utc(local))
    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    setpoint = calls[-1].data["temperature"] if calls else None
    hass.states.async_set(
        TRV,
        "heat",
        {"temperature": setpoint, "current_temperature": room_temp},
    )
    await hass.async_block_till_done()
    return setpoint


async def test_preheat_setpoint_held_until_occupied_time(
    hass, freezer, caplog
):
    """06:00 trigger → 20 °C held every tick → Normal takes over at 07:00."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    _, coordinator, calls = await _setup(hass, _config())

    assert await _tick(hass, freezer, coordinator, calls, "06:00", 17.0) == (
        NORMAL
    )
    room = coordinator.rooms["a"]
    assert room._preheat_active
    assert hass.states.get("sensor.a_period").state == PERIOD_PREHEAT
    assert any(m.startswith("preheat | room=a") for m in caplog.messages)

    pushes_after_trigger = len(calls)
    for local in ("06:01", "06:02", "06:30", "06:59"):
        assert (
            await _tick(hass, freezer, coordinator, calls, local, 17.5)
            == NORMAL
        )
        assert hass.states.get("sensor.a_period").state == PERIOD_PREHEAT
    assert len(calls) == pushes_after_trigger, "no 18 °C push in between"

    await _tick(hass, freezer, coordinator, calls, "07:00", 18.0)
    assert not room._preheat_active
    assert not room._preheat_in_progress
    assert room.current_period == PERIOD_NORMAL
    assert hass.states.get("sensor.a_period").state == PERIOD_NORMAL


async def test_convergence_records_sample_and_keeps_holding(hass, freezer):
    """Target reached after 06:20 → seen at 06:21; held until 07:00."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    await _tick(hass, freezer, coordinator, calls, "06:10", 18.5)
    await _tick(hass, freezer, coordinator, calls, "06:20", NORMAL)
    await _tick(hass, freezer, coordinator, calls, "06:21", NORMAL)

    samples = entry.runtime_data.preheat_samples["a"]
    # The room reports 20 °C after the 06:20 tick; seen at 06:21.
    assert [s["duration_minutes"] for s in samples] == [21]

    # Still holding the pre-heat setpoint after convergence.
    room = coordinator.rooms["a"]
    assert room._preheat_active
    assert room.current_period == PERIOD_PREHEAT
    assert calls[-1].data["temperature"] == NORMAL
    assert all(c.data["temperature"] != REDUCED for c in calls[1:])

    await _tick(hass, freezer, coordinator, calls, "07:00", NORMAL)
    assert room.current_period == PERIOD_NORMAL
    assert len(entry.runtime_data.preheat_samples["a"]) == 1


async def test_room_sensor_decides_warmth(hass, freezer):
    """Room sensor at 20 °C (TRV reads 17 °C) → room already warm."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    hass.states.async_set(SENSOR, str(NORMAL), {"device_class": "temperature"})
    _, coordinator, calls = await _setup(
        hass, _config(rooms={"a": {"temperature_sensor": SENSOR}})
    )

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    assert not coordinator.rooms["a"]._preheat_active
    assert all(c.data["temperature"] == REDUCED for c in calls)


async def test_no_preheat_when_zone_off(hass, freezer):
    """A zone that is off never pre-heats its rooms."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV,
        "heat",
        {"temperature": REDUCED, "current_temperature": 17.0},
    )
    _, coordinator, calls = await _setup(hass, _config(zone_mode=MODE_OFF))

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    assert not coordinator.rooms["a"]._preheat_active
    assert all(c.data["temperature"] != NORMAL for c in calls)


async def test_rebuild_keeps_running_preheat(hass, freezer):
    """A config edit during pre-heat keeps the run and its start time."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    start = coordinator.rooms["a"]._preheat_in_progress["start_time"]

    entry.runtime_data.runtime_config["default_zone"]["name"] = "Renamed"
    await _tick(hass, freezer, coordinator, calls, "06:05", 17.5)

    room = coordinator.rooms["a"]
    assert room._preheat_in_progress["start_time"] == start
    assert room.current_period == PERIOD_PREHEAT
    assert calls[-1].data["temperature"] == NORMAL

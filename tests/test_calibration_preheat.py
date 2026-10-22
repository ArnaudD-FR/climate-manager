# SPDX-License-Identifier: MIT
"""Offset calibration while a pre-heat runs, logs and restart seeding.

Scenarios:
- A steady 0.3 °C gap is ignored with the 0.5 °C threshold, but corrected
  while a pre-heat runs (PREHEAT_CALIBRATION_THRESHOLD = 0.2).
- Each offset written logs one INFO "calibrate |" line.
- Tado X valves: after a restart (empty memory) the new offset accumulates
  on the offset the valve reports, not on 0.
"""

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import DOMAIN


def _running_preheat() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "start_time": now,
        "start_temp": 19.0,
        "target_temp": 20.0,
        "until": now + timedelta(hours=1),
        "converged": False,
        "measuring": False,
    }


async def _setup(hass, area_id: str, trv: str, sensor: str):
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    config = entry.runtime_data.runtime_config
    config["calibration_enabled"] = True
    config["calibration_threshold"] = 0.5
    config.setdefault("rooms", {})[area_id] = {"temperature_sensor": sensor}
    entry.runtime_data.rooms = {area_id: [trv]}
    coordinator = entry.runtime_data.coordinator
    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    return coordinator, config, offset_calls


def _office_valve(hass, offset: str):
    """Office area with one Tado X valve reporting offset."""
    area = ar.async_get(hass).async_create("Office")
    tado_entry = MockConfigEntry(domain="tado_x", data={})
    tado_entry.add_to_hass(hass)
    valve = dr.async_get(hass).async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", "VA1")},
        model="Radiator Valve X",
        name="Vanne bureau",
    )
    dr.async_get(hass).async_update_device(valve.id, area_id=area.id)
    offset_sensor = er.async_get(hass).async_get_or_create(
        "sensor",
        "tado_x",
        "VA1_temperature_offset",
        config_entry=tado_entry,
        device_id=valve.id,
    )
    hass.states.async_set(offset_sensor.entity_id, offset)
    return area, valve


async def test_tighter_threshold_during_preheat(hass, freezer, caplog):
    """0.3 °C gap: skipped normally, corrected and logged in pre-heat."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    area, _ = _office_valve(hass, "-0.4")
    hass.states.async_set(
        "climate.office_trv",
        "heat",
        {"temperature": 20.0, "current_temperature": 20.0},
    )
    hass.states.async_set("sensor.office_temp", "19.7")
    coordinator, config, offset_calls = await _setup(
        hass, area.id, "climate.office_trv", "sensor.office_temp"
    )
    freezer.tick(timedelta(minutes=30))
    await coordinator._async_calibrate(config, ctx=object())
    await hass.async_block_till_done()
    assert not offset_calls

    coordinator.rooms[area.id]._preheat_in_progress = _running_preheat()
    await coordinator._async_calibrate(config, ctx=object())
    await hass.async_block_till_done()

    assert len(offset_calls) == 1
    assert offset_calls[0].data["offset"] == -0.7
    assert any(
        m.startswith(f"calibrate | room={area.id} trv=Vanne bureau")
        and "offset=-0.4→-0.7 threshold=0.2" in m
        for m in caplog.messages
    )


async def test_tado_valve_offset_seeded_from_sensor_after_restart(
    hass, freezer, caplog
):
    """Empty memory: the offset accumulates on the valve's reported one."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    area, valve = _office_valve(hass, "-1.2")
    hass.states.async_set(
        "climate.office",
        "heat",
        {"temperature": 20.0, "current_temperature": 20.6},
    )
    hass.states.async_set("sensor.office_temp", "19.9")

    coordinator, config, offset_calls = await _setup(
        hass, area.id, "climate.office", "sensor.office_temp"
    )
    assert not offset_calls  # readings not steady yet
    freezer.tick(timedelta(minutes=30))
    await coordinator._async_calibrate(config, ctx=object())
    await hass.async_block_till_done()

    assert len(offset_calls) == 1
    assert offset_calls[0].data == {"device_id": valve.id, "offset": -1.9}
    assert coordinator.calibrator.last_offset[valve.id] == -1.9
    assert any(
        m.startswith(f"calibrate | room={area.id} trv=Vanne bureau")
        and "offset=-1.2→-1.9 threshold=0.5" in m
        for m in caplog.messages
    )

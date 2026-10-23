# SPDX-License-Identifier: MIT
"""Viessmann ViCare (core vicare integration) boiler vendor.

The heating circuit's climate entity carries the heating curve
(heating_curve_slope, heating_curve_shift) and the boiler's own active
program (active_vicare_program) as attributes. The flow and outdoor
temperatures are sensors of the same device, recognised by their
translation key. A boiler with several heating circuits has one
supply_temperature sensor per circuit: the one with the climate entity's
circuit suffix ("-0") is taken, else the boiler-level one.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .base import BoilerReadings, BoilerVendor

_FLOW_KEY = "supply_temperature"
_BOILER_FLOW_KEY = "boiler_supply_temperature"
_OUTDOOR_KEY = "outside_temperature"


class ViCare(BoilerVendor):
    """Viessmann boilers through the vicare integration."""

    label = "ViCare"
    platform = "vicare"

    def readings(self, hass: HomeAssistant, entity_id: str) -> BoilerReadings:
        state = hass.states.get(entity_id)
        attrs = state.attributes if state is not None else {}
        program = attrs.get("active_vicare_program")
        sensors = _device_sensors(hass, entity_id)
        flow = _to_float(hass, sensors.get(_FLOW_KEY))
        if flow is None:
            flow = _to_float(hass, sensors.get(_BOILER_FLOW_KEY))
        return BoilerReadings(
            outdoor_temp=_to_float(hass, sensors.get(_OUTDOOR_KEY)),
            flow_temp=flow,
            curve_slope=_number(attrs.get("heating_curve_slope")),
            curve_shift=_number(attrs.get("heating_curve_shift")),
            program=program if isinstance(program, str) else None,
        )


def _device_sensors(hass: HomeAssistant, entity_id: str) -> dict[str, str]:
    """{translation_key: entity_id} of the sensors on entity_id's device.

    For a key present on several circuits, the one sharing entity_id's
    circuit suffix wins.
    """
    reg = er.async_get(hass)
    entry = reg.async_get(entity_id)
    if entry is None or entry.device_id is None:
        return {}
    circuit = entry.unique_id.rsplit("-", 1)[-1]
    result: dict[str, str] = {}
    for sensor in er.async_entries_for_device(reg, entry.device_id):
        key = sensor.translation_key
        if sensor.domain != "sensor" or key is None:
            continue
        own_circuit = sensor.unique_id.endswith(f"-{circuit}")
        if key not in result or own_circuit:
            result[key] = sensor.entity_id
    return result


def _to_float(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Numeric state of entity_id, None when missing or not a number."""
    state = hass.states.get(entity_id) if entity_id else None
    return _number(state.state) if state is not None else None


def _number(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

# SPDX-License-Identifier: MIT
"""Registered vendors and the helpers the core uses to query them.

The core never names a brand: it asks these helpers, which aggregate over
VENDORS (TRVs) and BOILER_VENDORS. Supporting a new brand means adding a
TRVVendor or BoilerVendor subclass here.
"""

from __future__ import annotations

import dataclasses

from homeassistant.core import HomeAssistant

from .base import BoilerReadings, BoilerVendor, CalibrationTarget, TRVVendor
from .tado_x import TadoX
from .vicare import ViCare

VENDORS: tuple[TRVVendor, ...] = (TadoX(),)
BOILER_VENDORS: tuple[BoilerVendor, ...] = (ViCare(),)

# Optional boiler config sensors overriding the vendor's readings, so any
# boiler (switch, input_boolean) can record them too.
_READING_SENSORS = {
    "outdoor_temp": "outdoor_temperature_entity_id",
    "flow_temp": "flow_temperature_entity_id",
}

__all__ = [
    "BOILER_VENDORS",
    "VENDORS",
    "BoilerReadings",
    "BoilerVendor",
    "CalibrationTarget",
    "TRVVendor",
    "accessory_models",
    "boiler_readings",
    "boiler_vendor",
    "calibration_targets",
    "cloud_polling",
    "pairable_entities",
    "suggest_mappings",
]


def calibration_targets(
    hass: HomeAssistant,
    area_id: str,
    entity_ids: list[str],
    mappings: dict[str, list[str]],
) -> list[CalibrationTarget]:
    """Every vendor's calibration targets for a room."""
    return [
        target
        for vendor in VENDORS
        for target in vendor.calibration_targets(
            hass, area_id, entity_ids, mappings
        )
    ]


def accessory_models() -> frozenset[str]:
    """Device models that are valve accessories, never a boiler."""
    return frozenset().union(*(v.accessory_models for v in VENDORS))


def pairable_entities(hass: HomeAssistant, entity_ids: list[str]) -> list[str]:
    """Entities of entity_ids that can be paired with Matter entities."""
    return sorted(
        eid
        for eid in entity_ids
        if any(v.pairable and v.owns(hass, eid) for v in VENDORS)
    )


def suggest_mappings(hass: HomeAssistant) -> dict[str, list[str]]:
    """Every vendor's suggested {entity: [Matter entities]} pairings."""
    result: dict[str, list[str]] = {}
    for vendor in VENDORS:
        result.update(vendor.suggest_mappings(hass))
    return result


def cloud_polling(hass: HomeAssistant) -> list[dict]:
    """[{vendor, interval}] for the vendors whose data is polled."""
    return [
        {"vendor": vendor.label, "interval": interval}
        for vendor in VENDORS
        if (interval := vendor.poll_interval(hass)) is not None
    ]


def boiler_vendor(hass: HomeAssistant, entity_id: str) -> BoilerVendor | None:
    """The vendor owning the boiler entity_id, if any."""
    for vendor in BOILER_VENDORS:
        if vendor.owns(hass, entity_id):
            return vendor
    return None


def boiler_readings(
    hass: HomeAssistant, boiler_config: dict | None
) -> BoilerReadings:
    """Heating conditions of the configured boiler (empty without one).

    The vendor's readings, overridden by the sensors set in the boiler
    config (a sensor set but unavailable reads None).
    """
    if not boiler_config:
        return BoilerReadings()
    vendor = boiler_vendor(hass, boiler_config["entity_id"])
    readings = (
        vendor.readings(hass, boiler_config["entity_id"])
        if vendor is not None
        else BoilerReadings()
    )
    overrides: dict[str, float | None] = {}
    for field, key in _READING_SENSORS.items():
        sensor = boiler_config.get(key)
        if sensor:
            state = hass.states.get(sensor)
            try:
                overrides[field] = float(state.state) if state else None
            except (TypeError, ValueError):
                overrides[field] = None
    return dataclasses.replace(readings, **overrides)

# SPDX-License-Identifier: MIT
"""Registered TRV vendors and the helpers the core uses to query them.

The core never names a brand: it asks these helpers, which aggregate over
VENDORS. Supporting a new brand means adding a TRVVendor subclass here.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .base import CalibrationTarget, TRVVendor
from .tado_x import TadoX

VENDORS: tuple[TRVVendor, ...] = (TadoX(),)

__all__ = [
    "VENDORS",
    "CalibrationTarget",
    "TRVVendor",
    "accessory_models",
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

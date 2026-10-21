# SPDX-License-Identifier: MIT
"""Vendor interface: what Climate Manager needs to know about a TRV brand.

The core only drives standard climate entities. Anything a brand does on
top of that (offset calibration, cloud entity paired with local Matter
valves, accessory devices) is described by a TRVVendor subclass. The
defaults mean "nothing special": a brand without a vendor class is pushed
setpoints and never calibrated.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


@dataclass(frozen=True)
class CalibrationTarget:
    """One offset to keep aligned on the room sensor.

    key: identifies the offset in the calibration memory (device_id when
         the offset belongs to a physical valve, else entity_id).
    name: shown in logs and in the panel.
    temp_entity_id: climate entity whose current_temperature is compared
         with the room sensor.
    entity_id: climate entity the panel row opens.
    device_id: physical device carrying the offset, when known.
    """

    vendor: TRVVendor
    key: str
    name: str
    temp_entity_id: str
    entity_id: str | None = None
    device_id: str | None = None


class TRVVendor:
    """Brand-specific behaviour; every method has a neutral default."""

    # Shown in the panel ("Tado X").
    label: str = ""
    # Integration domain whose entities this vendor owns.
    platform: str = ""
    # Device models whose switches belong to a valve, not to a boiler.
    accessory_models: frozenset[str] = frozenset()
    # True when the vendor's entities can be paired with Matter entities.
    pairable: bool = False

    def owns(self, hass: HomeAssistant, entity_id: str) -> bool:
        """True when entity_id belongs to this vendor's integration."""
        reg = er.async_get(hass).async_get(entity_id)
        return reg is not None and reg.platform == self.platform

    def calibration_targets(
        self,
        hass: HomeAssistant,
        area_id: str,
        entity_ids: list[str],
        mappings: dict[str, list[str]],
    ) -> list[CalibrationTarget]:
        """Offsets to calibrate in a room (none by default)."""
        return []

    def read_offset(
        self, hass: HomeAssistant, target: CalibrationTarget
    ) -> float | None:
        """Offset currently applied on the target, or None if unknown."""
        return None

    async def write_offset(
        self, hass: HomeAssistant, target: CalibrationTarget, offset: float
    ) -> None:
        """Apply an absolute offset to the target."""
        raise NotImplementedError

    def suggest_mappings(self, hass: HomeAssistant) -> dict[str, list[str]]:
        """Suggested {vendor entity: [Matter entities]} pairings."""
        return {}

    def poll_interval(self, hass: HomeAssistant) -> int | None:
        """Cloud refresh interval in seconds, when the data is polled."""
        return None

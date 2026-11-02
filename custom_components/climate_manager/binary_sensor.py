# SPDX-License-Identifier: MIT
"""Climate Manager boiler demand binary sensor.

On while at least one room needs heat (see boiler.py); its `rooms`
attribute lists them and `reasons` says why, so the recorder keeps when
and why the boiler was asked to heat. Exists only while a boiler is
configured: its device is removed by async_sync_devices once the boiler
is unconfigured.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import (
    ClimateManagerEntity,
    async_add_entities_for_ids,
    boiler_demand_unique_id,
    boiler_device_info,
)

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry
    from .coordinator import ClimateManagerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the boiler demand sensor once a boiler is configured."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities_for_ids(
        entry,
        lambda: ["boiler"] if coordinator.boiler is not None else [],
        lambda _: [BoilerDemandSensor(coordinator, entry)],
        async_add_entities,
    )


class BoilerDemandSensor(ClimateManagerEntity, BinarySensorEntity):
    """On while at least one room needs heat."""

    # No device class: HEAT would show "Normal" / "Hot" for a demand.
    _attr_translation_key = "boiler_demand"

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = boiler_demand_unique_id(entry.entry_id)
        self._attr_device_info = boiler_device_info()
        self.entity_id = "binary_sensor.climate_manager_boiler_demand"

    @property
    def is_on(self) -> bool | None:
        """True while at least one room needs heat."""
        boiler = self.coordinator.boiler
        return bool(boiler.demand_rooms) if boiler is not None else None

    @property
    def available(self) -> bool:
        """Unavailable once the boiler is unconfigured."""
        return self.coordinator.boiler is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Rooms needing heat, and why (period, valve, below_setpoint)."""
        boiler = self.coordinator.boiler
        if boiler is None:
            return {"rooms": [], "reasons": {}}
        return {
            "rooms": boiler.demand_rooms,
            "reasons": boiler.demand_reasons,
        }

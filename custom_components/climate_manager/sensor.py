# SPDX-License-Identifier: MIT
"""Climate Manager sensor platform — zone and room period sensors.

- Zone period: the zone time program's period (frost_protection when the
  zone is off). One per zone, on the zone device.
- Room period: the room's effective period after presence resolution
  (in time_program_presences mode rooms of one zone can differ). One per
  managed room, on the room device.

Both are enum sensors so the history panel renders them as a timeline.
Values are re-read from the coordinator's live domain objects by id on
every state write, because the coordinator rebuilds its Zone/Room graph
when the config changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import VALID_PERIODS
from .entity import (
    ClimateManagerEntity,
    async_add_entities_for_ids,
    room_device_info,
    zone_device_info,
)

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry
    from .coordinator import ClimateManagerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create zone and room period sensors; add new ones as they appear."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities_for_ids(
        entry,
        lambda: coordinator.zones,
        lambda zone_id: [ZonePeriodSensor(coordinator, entry, zone_id)],
        async_add_entities,
    )
    async_add_entities_for_ids(
        entry,
        lambda: coordinator.rooms,
        lambda area_id: [RoomPeriodSensor(coordinator, entry, area_id)],
        async_add_entities,
    )


class _PeriodSensor(ClimateManagerEntity, SensorEntity):
    """Enum sensor whose value is one of the four period names."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(VALID_PERIODS)

    def _period(self) -> str | None:
        """Return the raw period from the live domain object."""
        raise NotImplementedError

    @property
    def native_value(self) -> str | None:
        """Current period, or None before the first evaluation."""
        period = self._period()
        return period if period in VALID_PERIODS else None

    @property
    def available(self) -> bool:
        """Unavailable until evaluated, or once the zone/room is gone."""
        return self.native_value is not None


class ZonePeriodSensor(_PeriodSensor):
    """Zone period from the zone time program."""

    _attr_translation_key = "zone_period"

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone_id}_period"
        self._attr_device_info = zone_device_info(
            entry.runtime_data.runtime_config, zone_id
        )

    def _period(self) -> str | None:
        zone = self.coordinator.zones.get(self._zone_id)
        return zone.current_period if zone is not None else None


class RoomPeriodSensor(_PeriodSensor):
    """Room effective period (presence-resolved)."""

    _attr_translation_key = "room_period"

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
        area_id: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._area_id = area_id
        self._attr_unique_id = f"{entry.entry_id}_room_{area_id}_period"
        # The room device sits in its area and is named after it: HA would
        # generate sensor.<area>_<device>_period (area name twice). An
        # integration-set entity_id is used as-is (conflicts still resolved).
        self.entity_id = f"sensor.{area_id}_period"

    @property
    def device_info(self) -> DeviceInfo:
        """Room device in the room's HA area (hass is set before reading)."""
        return room_device_info(self.hass, self._area_id)

    def _period(self) -> str | None:
        room = self.coordinator.rooms.get(self._area_id)
        return room.current_period if room is not None else None

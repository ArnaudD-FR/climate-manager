# SPDX-License-Identifier: MIT
"""Climate Manager sensor platform — zone and room period sensors.

- Zone period: the zone time program's period (frost_protection when the
  zone is off). One per zone, on the zone device.
- Room period: the room's effective period after presence resolution
  (in time_program_presences mode rooms of one zone can differ), or
  "preheat" while pre-heat holds the upcoming setpoint. One per managed
  room, on the room device.

Both are enum sensors so the history panel renders them as a timeline.

- Room pre-heat parameters (diagnostic, measurement): the learned heating
  rate (min/°C, unknown while learning) and the learned boost factor, so
  their evolution shows in the history and long-term statistics.

Values are re-read from the coordinator's live domain objects by id on
every state write, because the coordinator rebuilds its Zone/Room graph
when the config changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PERIOD_PREHEAT, VALID_PERIODS
from .entity import (
    ClimateManagerEntity,
    async_add_entities_for_ids,
    room_device_info,
    room_period_unique_id,
    room_sensor_unique_id,
    zone_device_info,
    zone_period_unique_id,
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
        lambda area_id: [
            RoomPeriodSensor(coordinator, entry, area_id),
            RoomPreheatRateSensor(coordinator, entry, area_id),
            RoomBoostFactorSensor(coordinator, entry, area_id),
        ],
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
        self._attr_unique_id = zone_period_unique_id(entry.entry_id, zone_id)
        self._attr_device_info = zone_device_info(
            entry.runtime_data.runtime_config, zone_id
        )

    def _period(self) -> str | None:
        zone = self.coordinator.zones.get(self._zone_id)
        return zone.current_period if zone is not None else None


class RoomPeriodSensor(_PeriodSensor):
    """Room effective period (presence-resolved, or pre-heat)."""

    _attr_translation_key = "room_period"
    _attr_options = [*VALID_PERIODS, PERIOD_PREHEAT]

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
        area_id: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._area_id = area_id
        self._attr_unique_id = room_period_unique_id(entry.entry_id, area_id)
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

    @property
    def native_value(self) -> str | None:
        """Room period, including "preheat" while pre-heat holds."""
        period = self._period()
        return period if period in self._attr_options else None


class _RoomPreheatSensor(ClimateManagerEntity, SensorEntity):
    """A learned pre-heat parameter of a room (diagnostic measurement)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    # Sensor key: unique_id / entity_id suffix and translation key.
    _key: str = ""

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
        area_id: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._area_id = area_id
        self._attr_translation_key = self._key
        self._attr_unique_id = room_sensor_unique_id(
            entry.entry_id, area_id, self._key
        )
        # Same reason as RoomPeriodSensor: avoid the area name twice.
        self.entity_id = f"sensor.{area_id}_{self._key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Room device in the room's HA area (hass is set before reading)."""
        return room_device_info(self.hass, self._area_id)

    @property
    def available(self) -> bool:
        """Unavailable once the room is gone."""
        return self.coordinator.rooms.get(self._area_id) is not None


class RoomPreheatRateSensor(_RoomPreheatSensor):
    """Learned heating rate (min/°C); unknown while learning."""

    _key = "preheat_rate"
    _attr_native_unit_of_measurement = "min/°C"

    @property
    def native_value(self) -> float | None:
        room = self.coordinator.rooms.get(self._area_id)
        return room.learned_rate() if room is not None else None


class RoomBoostFactorSensor(_RoomPreheatSensor):
    """Learned pre-heat boost factor."""

    _key = "preheat_boost_factor"

    @property
    def native_value(self) -> float | None:
        room = self.coordinator.rooms.get(self._area_id)
        return room.boost_factor() if room is not None else None

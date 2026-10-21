# SPDX-License-Identifier: MIT
"""Climate Manager HA entity base class and device helpers.

Every zone gets one device (mode select + period sensor) and every managed
room gets one device (period sensor) so the recorder historises zone mode
changes, zone periods, and per-room effective periods.

Design decisions:
- Entities are push-only (should_poll=False): they subscribe to
  coordinator.async_add_listener and write state after every evaluation.
  HA only records a new state row when the value actually changes.
- Device identifiers: (DOMAIN, "zone_<zone_id>") / (DOMAIN, "room_<area_id>")
  / (DOMAIN, "boiler"). zone_id="default" is the Default Zone.
- Zone/room deletion is handled once, at device level, by
  async_sync_devices: removing a device removes its entities.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry
    from .coordinator import ClimateManagerCoordinator

MANUFACTURER = "Climate Manager"
_ZONE_PREFIX = "zone_"
_ROOM_PREFIX = "room_"
_BOILER_IDENT = "boiler"


def zone_mode_unique_id(entry_id: str, zone_id: str) -> str:
    """unique_id of a zone mode select."""
    return f"{entry_id}_zone_{zone_id}_mode"


def zone_period_unique_id(entry_id: str, zone_id: str) -> str:
    """unique_id of a zone period sensor."""
    return f"{entry_id}_zone_{zone_id}_period"


def room_period_unique_id(entry_id: str, area_id: str) -> str:
    """unique_id of a room period sensor."""
    return f"{entry_id}_room_{area_id}_period"


def room_sensor_unique_id(entry_id: str, area_id: str, key: str) -> str:
    """unique_id of a room sensor identified by key."""
    return f"{entry_id}_room_{area_id}_{key}"


def zone_config(config: dict, zone_id: str) -> dict | None:
    """Return the stored ZoneConfig for zone_id, or None if unknown."""
    if zone_id == "default":
        return config.get("default_zone")
    return config.get("zones", {}).get(zone_id)


def zone_name(config: dict, zone_id: str) -> str:
    """Return the display name of a zone (falls back to zone_id)."""
    cfg = zone_config(config, zone_id) or {}
    return cfg.get("name") or zone_id


def room_name(hass: HomeAssistant, area_id: str) -> str:
    """Return the HA area name for a room (falls back to area_id)."""
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else area_id


def zone_device_info(config: dict, zone_id: str) -> DeviceInfo:
    """Device info for a heating zone."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{_ZONE_PREFIX}{zone_id}")},
        name=zone_name(config, zone_id),
        manufacturer=MANUFACTURER,
        model="Heating zone",
    )


def boiler_demand_unique_id(entry_id: str) -> str:
    """Unique id of the boiler demand binary sensor."""
    return f"{entry_id}_boiler_demand"


def boiler_device_info() -> DeviceInfo:
    """Device info for the controlled boiler."""
    return DeviceInfo(
        identifiers={(DOMAIN, _BOILER_IDENT)},
        name="Boiler",
        manufacturer=MANUFACTURER,
        model="Boiler demand",
    )


def room_device_info(hass: HomeAssistant, area_id: str) -> DeviceInfo:
    """Device info for a managed room, placed in its HA area."""
    name = room_name(hass, area_id)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{_ROOM_PREFIX}{area_id}")},
        name=name,
        manufacturer=MANUFACTURER,
        model="Room",
        suggested_area=name,
    )


@callback
def async_sync_devices(
    hass: HomeAssistant, entry: ClimateManagerConfigEntry
) -> None:
    """Remove devices of deleted zones/rooms and refresh device names.

    Valid ids come from the coordinator's live domain graph (rebuilt from
    config at the start of each evaluation). A user-set name (name_by_user)
    still wins over the refreshed default name.
    """
    coordinator = entry.runtime_data.coordinator
    if coordinator is None:
        return
    config = entry.runtime_data.runtime_config
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        for domain, ident in device.identifiers:
            if domain != DOMAIN:
                continue
            if ident == _BOILER_IDENT:
                if coordinator.boiler is None:
                    dev_reg.async_remove_device(device.id)
                break
            if ident.startswith(_ZONE_PREFIX):
                zone_id = ident.removeprefix(_ZONE_PREFIX)
                exists = zone_id in coordinator.zones
                name = zone_name(config, zone_id) if exists else None
            elif ident.startswith(_ROOM_PREFIX):
                area_id = ident.removeprefix(_ROOM_PREFIX)
                exists = area_id in coordinator.rooms
                name = room_name(hass, area_id) if exists else None
            else:
                continue
            if not exists:
                dev_reg.async_remove_device(device.id)
            elif device.name != name:
                dev_reg.async_update_device(device.id, name=name)
            break


@callback
def async_add_entities_for_ids(
    entry: ClimateManagerConfigEntry,
    ids: Callable[[], Iterable[str]],
    factory: Callable[[str], list[Entity]],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add entities for current ids now, and for new ids after each cycle.

    Removed ids are only forgotten here — their devices (and thus their
    entities) are removed by async_sync_devices.
    """
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        current = list(ids())
        known.intersection_update(current)
        new = [item_id for item_id in current if item_id not in known]
        if not new:
            return
        known.update(new)
        async_add_entities(
            [entity for item_id in new for entity in factory(item_id)]
        )

    _async_add_new()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))


class ClimateManagerEntity(Entity):
    """Base class: push updates from the coordinator after each cycle."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
    ) -> None:
        self.coordinator = coordinator
        self._entry = entry

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates (auto-unsub on removal)."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write the latest state; HA dedupes unchanged values."""
        self.async_write_ha_state()

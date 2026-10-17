# SPDX-License-Identifier: MIT
"""Climate Manager select platform — one zone mode select per zone.

The select state is the zone mode stored in runtime_config, so every mode
change (panel WS command or this entity) lands in the recorder history.
Selecting an option goes through coordinator.async_set_zone_mode — the
same persist + OBS-01 log + re-evaluate path as the set_zone_mode WS
command.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import VALID_MODES
from .entity import (
    ClimateManagerEntity,
    async_add_entities_for_ids,
    zone_config,
    zone_device_info,
    zone_mode_unique_id,
)

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry
    from .coordinator import ClimateManagerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a mode select per zone; add new zones as they appear."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities_for_ids(
        entry,
        lambda: coordinator.zones,
        lambda zone_id: [ZoneModeSelect(coordinator, entry, zone_id)],
        async_add_entities,
    )


class ZoneModeSelect(ClimateManagerEntity, SelectEntity):
    """Zone mode: off / time_program / time_program_presences."""

    _attr_translation_key = "zone_mode"
    _attr_options = list(VALID_MODES)

    def __init__(
        self,
        coordinator: ClimateManagerCoordinator,
        entry: ClimateManagerConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._zone_id = zone_id
        self._attr_unique_id = zone_mode_unique_id(entry.entry_id, zone_id)
        self._attr_device_info = zone_device_info(
            entry.runtime_data.runtime_config, zone_id
        )

    @property
    def current_option(self) -> str | None:
        """Zone mode from the stored config (None if zone was deleted)."""
        cfg = zone_config(
            self._entry.runtime_data.runtime_config, self._zone_id
        )
        mode = cfg.get("mode") if cfg is not None else None
        return mode if mode in VALID_MODES else None

    @property
    def available(self) -> bool:
        """Unavailable once the zone no longer exists."""
        return self.current_option is not None

    async def async_select_option(self, option: str) -> None:
        """Persist the new zone mode and trigger a re-evaluation."""
        try:
            await self.coordinator.async_set_zone_mode(self._zone_id, option)
        except KeyError as err:
            raise HomeAssistantError(
                f"Zone {self._zone_id!r} not found"
            ) from err
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Failed to set zone mode: {err}") from err
        # Config already holds the new mode — record it immediately rather
        # than waiting for the scheduled evaluation to notify listeners.
        self.async_write_ha_state()

"""Climate Manager — Home Assistant custom integration.

Manages home climate controls through smart radiator thermostats.
Provides global heating modes, weekday-based time programs,
per-room schedule overrides, and person presence tracking.

This module is the integration entry point:
- async_setup_entry: loads Store + runs discovery + wires runtime_data
- async_unload_entry: unloads platform entities (PLATFORMS is empty in Phase 1)

Pattern: entry.runtime_data typed dataclass (modern HA pattern, April 2024 blog).
Anti-pattern avoided: global hass.data dict is NOT used (T-01-11).
"""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .discovery import discover_persons, discover_rooms
from .storage import ClimateManagerStore

# Entity platforms managed by this integration.
# Empty in Phase 1 — coordinator and platform entities are wired in Phase 2.
PLATFORMS: list[str] = []


@dataclass
class ClimateManagerData:
    """Runtime state for the Climate Manager integration.

    Stored on entry.runtime_data (Pattern 2 — modern typed runtime_data).
    Auto-cleaned by HA on unload. Never written to the global hass.data dict.

    Attributes:
        store: The ClimateManagerStore instance for persistence.
        runtime_config: Merged configuration (DEFAULT_CONFIG + sparse stored data).
        rooms: Discovered rooms {area_id: [climate_entity_ids]}.
        persons: Discovered persons [person.* entity_ids].
    """

    store: ClimateManagerStore
    runtime_config: dict
    rooms: dict[str, list[str]]
    persons: list[str]


# Modern typed ConfigEntry alias (Pattern 2 — entry.runtime_data pattern).
type ClimateManagerConfigEntry = ConfigEntry[ClimateManagerData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
) -> bool:
    """Set up Climate Manager from a config entry.

    Wires storage + discovery into entry.runtime_data.
    Does NOT start any coordinator, scheduler, or time-interval listener
    (Phase 2 scope — Pitfall 1: no ghost listeners in Phase 1).

    Steps:
    1. Construct Store and load merged configuration.
    2. Discover rooms from area + entity registries.
    3. Discover persons from entity registry.
    4. Assign all to entry.runtime_data.
    """
    store = ClimateManagerStore(hass)
    runtime_config = await store.async_load()
    rooms = await discover_rooms(hass)
    persons = await discover_persons(hass)

    entry.runtime_data = ClimateManagerData(
        store=store,
        runtime_config=runtime_config,
        rooms=rooms,
        persons=persons,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
) -> bool:
    """Unload a Climate Manager config entry.

    Required even though PLATFORMS is empty — HA needs this to mark the
    integration as reloadable and clean up cleanly (Pitfall 1, T-01-10).
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

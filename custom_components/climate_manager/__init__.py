"""Climate Manager — Home Assistant custom integration.

Manages home climate controls through smart radiator thermostats.
Provides global heating modes, weekday-based time programs,
per-room schedule overrides, and person presence tracking.

This module is the integration entry point:
- async_setup_entry: loads Store + runs discovery + wires runtime_data + coordinator
- async_unload_entry: cancels scheduler first, then unloads platform entities

Pattern: entry.runtime_data typed dataclass (modern HA pattern, April 2024 blog).
Anti-pattern avoided: global hass.data dict is NOT used (T-01-11).

Phase 2 additions:
- ClimateManagerData extended with coordinator and cancel_scheduler fields
- async_setup_entry wires coordinator and registers minute-polling scheduler (D-01)
- async_setup_entry calls coordinator.async_evaluate() immediately for restart recovery (INFRA-03)
- async_unload_entry cancels the scheduler before unloading platforms (Pitfall 1)
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .coordinator import ClimateManagerCoordinator
from .discovery import discover_persons, discover_rooms
from .storage import ClimateManagerStore

# Entity platforms managed by this integration.
# Empty in Phase 2 — pure backend, no platform entities (D-09).
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
        coordinator: The ClimateManagerCoordinator instance (Phase 2).
        cancel_scheduler: Cancel callback returned by async_track_time_interval (Phase 2).
    """

    store: ClimateManagerStore
    runtime_config: dict
    rooms: dict[str, list[str]]
    persons: list[str]
    # Phase 2 additions — use field(default=None) to avoid mutable default error (Pitfall 5).
    # String annotations used to avoid import cycle (coordinator.py imports ClimateManagerData).
    coordinator: "ClimateManagerCoordinator | None" = field(default=None)
    cancel_scheduler: "Callable[[], None] | None" = field(default=None)


# Modern typed ConfigEntry alias (Pattern 2 — entry.runtime_data pattern).
type ClimateManagerConfigEntry = ConfigEntry[ClimateManagerData]

# Explicit public API — prevents silent breakage if imports are reorganised.
__all__ = ["ClimateManagerData", "ClimateManagerConfigEntry", "ClimateManagerCoordinator"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
) -> bool:
    """Set up Climate Manager from a config entry.

    Wires storage + discovery + coordinator + scheduler into entry.runtime_data.

    Steps:
    1. Construct Store and load merged configuration.
    2. Discover rooms from area + entity registries.
    3. Discover persons from entity registry.
    4. Assign all to entry.runtime_data.
    5. Construct ClimateManagerCoordinator and store on runtime_data.coordinator.
    6. Push correct temperatures immediately (INFRA-03 — restart recovery).
    7. Register minute-polling scheduler; store cancel callback (D-01, Pitfall 1).
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

    # Phase 2: wire coordinator and scheduler
    coordinator = ClimateManagerCoordinator(hass, entry.runtime_data)
    entry.runtime_data.coordinator = coordinator

    # INFRA-03: immediate push on startup before first scheduler tick.
    # _last_pushed is empty on restart → push always fires (D-04).
    await coordinator.async_evaluate()

    # Register minute-polling scheduler; store cancel callback for clean unload (Pitfall 1).
    entry.runtime_data.cancel_scheduler = async_track_time_interval(
        hass,
        coordinator.async_evaluate,
        timedelta(minutes=1),
        name="climate_manager_scheduler",
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
) -> bool:
    """Unload a Climate Manager config entry.

    Cancels the scheduler FIRST to prevent ghost listeners (Pitfall 1, T-01-10),
    then unloads platform entities (PLATFORMS is empty in Phase 2 — D-09).
    """
    # Cancel scheduler before unloading platforms — no ghost listeners (Pitfall 1)
    if entry.runtime_data.cancel_scheduler is not None:
        entry.runtime_data.cancel_scheduler()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

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

Phase 3 additions:
- async_setup_entry registers 8 WebSocket commands via cm_ws.async_register_commands
- async_setup_entry serves www/ directory as a static path (Pitfall 6 — cache_headers=False)
- async_setup_entry registers sidebar panel via panel_custom.async_register_panel
- manifest.json declares dependencies ["http", "frontend", "panel_custom"] (Pitfall 7)
"""

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Callable

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .coordinator import ClimateManagerCoordinator
from .discovery import discover_persons, discover_room_sensors, discover_rooms
from .storage import ClimateManagerStore
from . import websocket as cm_ws
from .const import DOMAIN

# Entity platforms managed by this integration.
# Empty in Phase 2 — pure backend, no platform entities (D-09).
PLATFORMS: list[str] = []

# Panel registration constants (Phase 3)
# PANEL_URL: URL path where www/ directory is served (static files).
# PANEL_COMPONENT_NAME: must exactly match customElements.define("name", ...) in panel.js
#                       (RESEARCH Pitfall 2 — mismatch causes blank panel).
PANEL_URL = "/climate_manager_panel"
PANEL_COMPONENT_NAME = "climate-manager-panel"


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
    room_auto_sensors: dict[str, dict[str, str]]
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
    room_auto_sensors = await discover_room_sensors(hass)

    entry.runtime_data = ClimateManagerData(
        store=store,
        runtime_config=runtime_config,
        rooms=rooms,
        persons=persons,
        room_auto_sensors=room_auto_sensors,
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

    # Phase 3: register WebSocket commands (auto-unregister on entry unload — RESEARCH Pattern 3).
    cm_ws.async_register_commands(hass, entry)

    # Phase 3: serve www/ directory as a static path (cache_headers=False — RESEARCH Pitfall 6).
    www_path = Path(__file__).parent / "www"
    # Create www/ directory if missing so registration does not fail before Wave 3 produces panel.js.
    # Use executor job to avoid blocking the event loop (RESEARCH Pitfall 2).
    await hass.async_add_executor_job(www_path.mkdir, 0o755, True, True)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL, str(www_path), False)]
    )

    # Phase 3: register sidebar panel (panel_custom loaded via manifest dependency — Pitfall 7).
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=DOMAIN,
        webcomponent_name=PANEL_COMPONENT_NAME,
        sidebar_title="Climate Manager",
        sidebar_icon="mdi:thermometer",
        module_url=f"{PANEL_URL}/panel.js",
        embed_iframe=False,
        require_admin=False,
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

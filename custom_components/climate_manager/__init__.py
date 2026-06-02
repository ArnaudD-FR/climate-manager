# SPDX-License-Identifier: MIT
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

Bug fix — entity discovery refresh:
- async_setup_entry registers listeners on entity_registry_updated and
  device_registry_updated events to re-run discover_rooms / discover_room_sensors
  whenever a climate entity is added, removed, or its device's area changes.
  The cancel callbacks are stored in cancel_registry_listeners and called on unload.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Callable

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

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
        room_auto_sensors: Auto-discovered temperature/humidity sensors per area.
        coordinator: The ClimateManagerCoordinator instance (Phase 2).
        cancel_scheduler: Cancel callback returned by async_track_time_interval (Phase 2).
        cancel_registry_listeners: List of cancel callbacks for entity/device registry
            listeners. Called on unload to prevent ghost listeners.
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
    # Registry listeners — list of unsub callables, one per registered listener.
    cancel_registry_listeners: "list[Callable[[], None]]" = field(
        default_factory=list
    )
    # Phase 12 pre-heat store + in-memory samples (D-06).
    # preheat_store: the Store instance for persisting inertia samples.
    # preheat_samples: per-room sample lists {area_id: [{duration_minutes,
    #   timestamp}, ...]} loaded at setup and written only on sample change.
    preheat_store: "Store | None" = field(default=None)
    preheat_samples: dict = field(default_factory=dict)


# Modern typed ConfigEntry alias (Pattern 2 — entry.runtime_data pattern).
type ClimateManagerConfigEntry = ConfigEntry[ClimateManagerData]

# Explicit public API — prevents silent breakage if imports are reorganised.
__all__ = [
    "ClimateManagerData",
    "ClimateManagerConfigEntry",
    "ClimateManagerCoordinator",
]


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
    8. Register entity/device registry listeners for live room re-discovery.
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

    # Phase 12: wire preheat Store and load sample data (D-06).
    # key="climate_manager_preheat" — separate from main Store to keep
    # sample data isolated from room/person config (RESEARCH Open Q2).
    preheat_store = Store(hass, version=1, key="climate_manager_preheat")
    preheat_samples: dict = await preheat_store.async_load() or {}
    entry.runtime_data.preheat_store = preheat_store
    entry.runtime_data.preheat_samples = preheat_samples

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
        sidebar_icon="mdi:home-thermometer",
        module_url=f"{PANEL_URL}/panel.js",
        embed_iframe=False,
        require_admin=False,
    )

    # Bug fix: live entity re-discovery.
    #
    # discover_rooms() is called once at startup; newly added integrations (e.g.
    # Tado X) register their climate entities after async_setup_entry has already
    # run, so those entities never appear in entry.runtime_data.rooms.
    #
    # Fix: listen to entity_registry_updated and device_registry_updated events.
    # - entity_registry_updated fires when a climate entity is created or removed.
    # - device_registry_updated fires when a device's area_id changes (i.e. user
    #   assigns a device with climate entities to an area for the first time, or
    #   moves it to a different area).
    # On either event, re-run discover_rooms + discover_room_sensors and update
    # the live runtime_data so the next get_status / subscribe_status push
    # reflects the new entity set without requiring an HA restart.
    #
    # Implementation note: the listeners are @callback (sync) to satisfy HA's
    # bus contract. Re-discovery is async so we schedule it as a task via
    # hass.async_create_task. The coordinator.async_evaluate() call inside the
    # task fires a subscribe_status push so connected panels refresh immediately.

    @callback
    def _handle_entity_registry_updated(event: Event) -> None:
        """Re-discover rooms when a climate entity is added, removed, or disabled/re-enabled."""
        action = event.data.get("action")
        entity_id = event.data.get("entity_id", "")
        if not entity_id.startswith("climate."):
            return
        if action in ("create", "remove"):
            pass  # always re-discover
        elif action == "update":
            # Re-discover only when disability status or area assignment changes.
            changes = event.data.get("changes", {})
            if "disabled_by" not in changes and "area_id" not in changes:
                return
        else:
            return
        hass.async_create_task(
            _async_refresh_rooms(hass, entry),
            name="climate_manager_refresh_rooms_entity",
        )

    @callback
    def _handle_device_registry_updated(event: Event) -> None:
        """Re-discover rooms when a device's area assignment changes."""
        action = event.data.get("action")
        if action != "update":
            return
        changes = event.data.get("changes", {})
        # Only react when area_id changed — the change that affects room discovery.
        if "area_id" not in changes:
            return
        hass.async_create_task(
            _async_refresh_rooms(hass, entry),
            name="climate_manager_refresh_rooms_device",
        )

    cancel_entity = hass.bus.async_listen(
        er.EVENT_ENTITY_REGISTRY_UPDATED, _handle_entity_registry_updated
    )
    cancel_device = hass.bus.async_listen(
        dr.EVENT_DEVICE_REGISTRY_UPDATED, _handle_device_registry_updated
    )
    entry.runtime_data.cancel_registry_listeners = [
        cancel_entity,
        cancel_device,
    ]

    return True


async def _async_refresh_rooms(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
) -> None:
    """Re-discover rooms and room sensors, update runtime_data, and push status.

    Runs discover_rooms() + discover_room_sensors() against the current live
    registries (entity + device + area) and replaces entry.runtime_data.rooms
    and entry.runtime_data.room_auto_sensors in-place.  Then triggers a
    coordinator evaluation so the next subscribe_status push reflects the
    updated room list.

    This function is safe to call concurrently — HA's registry helpers are
    non-blocking coroutines and runtime_data is only mutated from the event loop.
    """
    new_rooms = await discover_rooms(hass)
    new_sensors = await discover_room_sensors(hass)
    entry.runtime_data.rooms = new_rooms
    entry.runtime_data.room_auto_sensors = new_sensors
    if entry.runtime_data.coordinator is not None:
        await entry.runtime_data.coordinator.async_evaluate()


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ClimateManagerConfigEntry,
) -> bool:
    """Unload a Climate Manager config entry.

    Cancels the scheduler and registry listeners FIRST to prevent ghost listeners
    (Pitfall 1, T-01-10), then unloads platform entities (PLATFORMS is empty in
    Phase 2 — D-09).
    """
    # Cancel scheduler before unloading platforms — no ghost listeners (Pitfall 1)
    if entry.runtime_data.cancel_scheduler is not None:
        entry.runtime_data.cancel_scheduler()

    # Cancel entity/device registry listeners (bug fix — live re-discovery).
    for cancel in entry.runtime_data.cancel_registry_listeners:
        cancel()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

---
slug: tado-x-entities-not-in-rooms
status: resolved
trigger: user
goal: find_and_fix
tdd_mode: false
created: 2026-05-27
resolved: 2026-05-27
---

# Debug: Tado X entities not visible in room configuration

## Symptoms

After adding a new Tado X integration in Home Assistant (which exposes new
`climate` entities), the Climate Manager frontend panel does not show those new
entities when configuring rooms. The entities exist in HA but Climate Manager
cannot see or display them in the room entity selector.

## Hypotheses

- H1: The backend WebSocket handler that lists available climate entities uses a
  stale cache or one-time discovery at startup, missing entities registered
  after the integration loads. **CONFIRMED**
- H2: There is an allow-list, filter, or prefix check in entity discovery that
  excludes Tado X entity IDs. — not the case
- H3: The frontend requests the entity list once (on panel load) and does not
  re-fetch after HA state changes. — not the primary cause
- H4: The entity list is sourced from stored config (e.g. Store), not from live
  HA entity registry, so newly added entities are invisible until config is
  updated. — partial (rooms dict, not Store)

## Current Focus

hypothesis: RESOLVED — H1 confirmed next_action: closed

## Evidence

- timestamp: 2026-05-27 file: custom_components/climate_manager/**init**.py
  observation: discover_rooms() is called exactly once in async_setup_entry
  (line 109). The result is stored in entry.runtime_data.rooms. No subsequent
  call is ever made to refresh it.

- timestamp: 2026-05-27 file: custom_components/climate_manager/coordinator.py
  observation: \_build_status_payload() (line 306) and async_evaluate()
  (line 114) both iterate over self.\_data.rooms — the stale startup dict.
  Neither re-calls discover_rooms().

- timestamp: 2026-05-27 file: custom_components/climate_manager/websocket.py
  observation: ws_get_status (line 141) also reads entry.runtime_data.rooms
  directly. ws_get_config (line 222-228) DOES query the live entity registry for
  climate_entities, but this list is not used for the rooms display.

- timestamp: 2026-05-27 file: frontend/src/components/rooms-tab.ts observation:
  The Rooms tab renders from status.rooms_status (from get_status /
  subscribe_status), which is sourced from entry.runtime_data.rooms on the
  backend. So the frontend correctly reflects whatever the backend sends, but
  the backend never refreshes its room map.

## Resolution

root_cause: discover_rooms() was called once at integration startup and stored
in entry.runtime_data.rooms. No mechanism existed to refresh this map when new
climate entities (e.g. from a freshly added Tado X integration) were registered
in HA's entity registry after startup. Both the coordinator status push and the
get_status WebSocket handler read from this stale dict, so new entities were
invisible to the panel without an HA restart.

fix: Added two event listeners in async_setup_entry registered via
hass.bus.async_listen:

1. entity_registry_updated (action=create/remove, entity_id starts with
   "climate.") — fires when a new climate entity is registered.
2. device_registry_updated (action=update, changes includes "area_id") — fires
   when a device's area assignment changes. Both listeners schedule
   \_async_refresh_rooms() as a background task, which re-runs
   discover_rooms() + discover_room_sensors() and replaces
   entry.runtime_data.rooms and entry.runtime_data.room_auto_sensors, then calls
   coordinator.async_evaluate() to push an updated subscribe_status event to all
   connected panels immediately. The cancel callbacks are stored in
   entry.runtime_data.cancel_registry_listeners (a new list field on
   ClimateManagerData) and called in async_unload_entry to prevent ghost
   listeners. File changed: custom_components/climate_manager/**init**.py

---
status: resolved
commit: 9117231
trigger: room entities should be dynamic but a removed entity is still present
created: 2026-05-28
updated: 2026-05-28
---

# Debug: room-entity-not-found-ghost-card

## Symptom
Screenshot shows 3 hui-thermostat-card instances in a room's Climate Entities section:
"Tado - Bureau" (valid), "Entity not found" (ghost), "Bureau" (valid).

## Root Cause
Two-part bug in the backend discovery/listener:

**1. discover_rooms() includes disabled entities.**
`discovery.py` Pass 1 and Pass 2 iterate `entity_reg.entities.values()` with no
`disabled_by` filter. A disabled climate entity remains in the entity registry but has
no state in `hass.states` → appears in `rooms_status.entity_ids` → frontend creates a
`hui-thermostat-card` that shows "Entity not found".

**2. entity_registry_updated handler ignores "update" action.**
`__init__.py` `_handle_entity_registry_updated` only re-discovers on "create"/"remove".
Disabling an entity fires action="update", not "remove" → re-discovery is not triggered
→ disabled entity stays in `runtime_data.rooms`.

## Fix
1. `discovery.py`: Add `and not entry.disabled_by` to both passes of `discover_rooms()`
2. `__init__.py`: Extend listener to handle action="update" when `disabled_by` or `area_id` changes in `changes` dict

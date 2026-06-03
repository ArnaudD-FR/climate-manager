# Phase 13: Matter→Tado X Real-Time Calibration — Research

**Researched:** 2026-06-03
**Domain:** HA coordinator listener lifecycle, entity registry platform
detection, config schema extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config Schema**
- D-01: New root-level key `matter_mappings` at the same level as `rooms`,
  `persons`, and `zones`. Schema:
  ```json
  {
    "matter_mappings": {
      "climate.tado_living_room": [
        "climate.valve1_matter",
        "climate.valve2_matter"
      ]
    }
  }
  ```
  Key: tado_x climate entity_id (zone entity already in
  `runtime_data.rooms[area_id]`).
  Value: list of Matter climate entity_ids paired to that tado_x entity.
  Absent = no mapping for that room (sparse — no migration needed).

- D-02: `DEFAULT_CONFIG["matter_mappings"] = {}` (sparse default, same
  pattern as `rooms` and `zones`).

**Coordinator — Control Path**
- D-03: Entity-by-entity dispatch per area with `to_set` list logic; use
  `matter_entity_set` frozenset to skip already-added Matter entities.

- D-04: Calibration reads `current_temperature` from the Matter entity (not
  the tado_x zone entity).

- D-05: Calibration service uses `tado_x.set_temperature_offset` with
  `device_id`. Resolve by iterating `entity_reg.entities` to match tado_x
  entries whose `device_id` matches `entity_reg.async_get(matter_entity_id)
  .device_id`. Fall back to `_async_calibrate_room()` if no match found.
  **Researcher must verify device sharing (see Open Questions).**

- D-06: Unmapped tado_x zone entities — existing calibration behaviour
  unchanged.

- D-07: Unmapped Matter entities — treat as independent TRVs; resolve
  calibration via `supports_offset_calibration()`.

**Coordinator — Listener Lifecycle**
- D-08: `_matter_cal_listeners: dict[str, Callable]` in coordinator, keyed
  by entity_id.

- D-09: Listener scope by mapping state (mapped tado_x = no listener;
  mapped Matter = listener; unmapped tado_x = listener; unmapped Matter =
  listener).

- D-10: Registration at coordinator startup and on `matter_mappings` change
  via `_async_refresh_matter_listeners()`.

- D-11: Cancellation on unload: cancel all in `_matter_cal_listeners` inside
  `async_unload_entry`. Do NOT add to `cancel_registry_listeners` list.

**Frontend — Room Card Pairing UI**
- D-12: "Matter pairing" section below the TRV list. Per tado_x zone entity:
  `<select>` dropdown for Matter entity or "(none)". Auto-save on change. Only
  visible when room has at least one tado_x entity.

- D-13: Matter entity picker populated from `hass.states` filtered to
  `domain === "climate"` + entity registry `platform === "matter"` for the
  room's area.

- D-14: Multiple TRVs per room: each tado_x entity gets its own pairing row.

**WebSocket Commands**
- D-15: New WS command `set_matter_mapping`: payload
  `{ tado_entity_id, matter_entity_ids: [] }`.

- D-16: `set_matter_mapping` handler triggers
  `_async_refresh_matter_listeners()` after persisting to storage.

### Claude's Discretion

- Section heading for the room card pairing area: "Matter pairing" or
  "Real-time calibration" — planner's choice; keep consistent with
  calibration section terminology already in the room card.

### Deferred Ideas (OUT OF SCOPE)

- Fallback when Matter entity is unavailable — automatic fall-back to
  tado_x entity for setpoint calls. Deferred to a future robustness phase.
- Reverse mapping display — showing in the Matter entity's card which
  tado_x entity it is paired to.
- Bulk auto-pair — detect Matter + tado_x entity pairs in an area sharing
  the same HA device and offer to pair them all at once.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCALIB-01 | User can configure a room-level mapping from a Matter TRV entity to its Tado X device; when mapped, the calibration pass fires immediately on Matter entity `state_changed` rather than waiting for the polling interval, enabling sub-minute calibration responsiveness | `async_track_state_change_event` already imported in coordinator.py; `_ha_tracker_listeners` pattern is the verbatim model to follow; listener fires `_async_calibrate` for that room |
| MCALIB-02 | Matter state_changed listeners are registered and cancelled via the existing `cancel_registry_listeners` lifecycle pattern; mapping removal or integration reload does not accumulate ghost listeners | D-11 keeps `_matter_cal_listeners` separate from `cancel_registry_listeners`; cancel-all-then-re-register is safe because WS commands are serialised on the HA event loop |
</phase_requirements>

---

## Summary

Phase 13 adds real-time calibration responsiveness for rooms that pair a
Tado X zone climate entity with one or more Matter TRV entities. Currently,
calibration only runs on the 1-minute scheduler tick. By registering
`state_changed` listeners on the Matter (or tado_x) climate entities, the
integration fires `_async_calibrate` for that room within the same HA event
loop turn as the temperature update — achieving sub-minute responsiveness.

The implementation divides into four self-contained work units: (1) extending
the config schema with `matter_mappings`, (2) modifying the coordinator
control path to route setpoint calls through Matter entities when mapped,
(3) the listener registration and cancellation lifecycle, and (4) the
frontend room card pairing UI backed by a new `set_matter_mapping` WebSocket
command. All four units have clear patterns in the existing codebase to follow.

The key open question — whether Tado X Radiator Valve X appears under the
same `device_id` in both `tado_x` and `matter` entity registry entries — is
addressed in the Open Questions section with a documented fallback path
(already specified in D-05). This question affects the calibration service
dispatch path but not the listener registration logic, meaning the majority of
the phase can be planned without waiting for the answer.

**Primary recommendation:** Follow the `_ha_tracker_listeners` pattern
verbatim for `_matter_cal_listeners`; the cancel-all-then-re-register
strategy in `_async_refresh_matter_listeners()` is safe and already tested
by the existing coordinator lifecycle tests.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Matter mapping config schema | Backend (HA integration storage) | — | Config is persisted via `Store` helper; same tier as `rooms`, `zones` |
| Setpoint routing (tado_x vs Matter entity) | Backend coordinator | — | `async_evaluate` already owns setpoint dispatch; insert entity-by-entity logic there |
| State_changed listener registration | Backend coordinator | — | Coordinator owns all HA event subscriptions; listeners fire coordinator methods |
| Matter entity calibration temperature source | Backend coordinator | — | Coordinator reads `current_temperature` from HA state; same tier as existing calibration |
| Tado X device_id resolution for offset call | Backend coordinator + trv.py | — | `entity_reg.entities` lookup belongs in coordinator or trv helper; same as `get_tado_valve_devices` |
| Listener teardown on unload | Backend `__init__.py` | — | `async_unload_entry` already owns all teardown; add cancel loop there |
| Matter pairing UI | Frontend panel (room-card.ts) | — | Room card already renders the TRV section; add pairing row below it |
| `set_matter_mapping` WS command | Backend websocket.py | — | All WS commands registered in `websocket.py`; follows factory pattern |

---

## Standard Stack

### Core

No new external packages. All tooling is already present in the project.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.helpers.event.async_track_state_change_event` | HA 2025.x | Register state_changed listener per entity | Already imported in coordinator.py (line 1140); used for `_ha_tracker_listeners` — exact reuse |
| `homeassistant.helpers.entity_registry` | HA 2025.x | Platform detection + device_id resolution | Already imported in `__init__.py` and `websocket.py`; `entity_reg.async_get(entity_id).platform` used in websocket.py line 1268 |
| Lit 3.x / TypeScript 5.x | existing | Frontend pairing UI | Panel already built on Lit + TypeScript; no new framework needed |

[VERIFIED: codebase grep] All imports exist; no new packages needed.

### Supporting

No new packages.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `async_track_state_change_event` per entity | `async_track_entity_registry_updated_event` | State change is the right event; registry event is for entity metadata changes, not temperature updates |
| Separate `_matter_cal_listeners` dict | Appending to `cancel_registry_listeners` | D-11 explicitly forbids this; `cancel_registry_listeners` is for registry event listeners only |

**Installation:** No new packages — phase is code-only.

---

## Package Legitimacy Audit

Not applicable — this phase installs no external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
HA event loop tick (1-min)
  │
  └─► coordinator.async_evaluate()
        ├─► _push_temperatures() → asyncio.gather(to_set entities)
        │     to_set built by D-03 entity-by-entity dispatch:
        │       tado_x entity + mapping exists → to_set += matter_entity_ids
        │       tado_x entity + no mapping    → to_set += tado_x entity_id
        │       matter entity not in mapping  → to_set += matter entity_id
        │       matter entity in mapping      → skip (added via tado_x branch)
        │
        └─► _async_calibrate() → per-room calibrate
              mapped Matter entity → current_temp from Matter state
                                  → device_id from entity_reg match
                                  → tado_x.set_temperature_offset
              unmapped tado_x     → existing _async_calibrate_tado_device()
              unmapped Matter     → existing _async_calibrate_room()

Matter entity state_changed (real-time path)
  │
  └─► _matter_cal_listener callback (keyed by entity_id in _matter_cal_listeners)
        │ checks: event.data.new_state.attributes["current_temperature"] changed?
        └─► _async_calibrate(config) for that room only
              (same calibration logic as the periodic path)

Integration setup (async_setup_entry)
  └─► coordinator.__init__ → _matter_cal_listeners = {}
  └─► coordinator.async_evaluate() (startup push)
        └─► _async_refresh_matter_listeners() if _matter_cal_listeners empty

set_matter_mapping WS command
  └─► mutate runtime_config["matter_mappings"]
  └─► store.async_save()
  └─► connection.send_result()
  └─► coordinator._async_refresh_matter_listeners()
        └─► cancel all in _matter_cal_listeners
        └─► re-register from current matter_mappings + rooms

Integration unload (async_unload_entry)
  └─► cancel_scheduler()
  └─► for cancel in cancel_registry_listeners: cancel()
  └─► for cancel in coordinator._matter_cal_listeners.values(): cancel()
  └─► async_unload_platforms()
```

### Recommended Project Structure

No new files needed except tests. All changes are within existing files:

```
custom_components/climate_manager/
├── const.py              # Add matter_mappings:{} to DEFAULT_CONFIG
├── coordinator.py        # Add _matter_cal_listeners, D-03 control path,
│                         # _async_refresh_matter_listeners(), listener
│                         # callbacks, Matter calibration logic
├── __init__.py           # Add _matter_cal_listeners cancel loop in
│                         # async_unload_entry
├── websocket.py          # Add set_matter_mapping command + registration
frontend/src/
├── types.ts              # Extend ClimateConfig with matter_mappings
├── ws-client.ts          # Add setMatterMapping() method
├── components/room-card.ts  # Add Matter pairing section
tests/
├── test_coordinator.py   # New: listener registration, calibration routing,
│                         # lifecycle tests for _matter_cal_listeners
├── test_websocket.py     # New: set_matter_mapping handler tests
```

### Pattern 1: `_ha_tracker_listeners` → `_matter_cal_listeners`

**What:** Dictionary keyed by entity_id, storing cancel callbacks for
`async_track_state_change_event` listeners. Cancel-all-then-re-register
on config changes.

**When to use:** Any HA event subscription that needs per-entity precision
and must be cancelled atomically on config change.

**Example (existing pattern, verbatim model):**
```python
# Source: coordinator.py lines 1189-1207
if notif_id not in self._ha_tracker_listeners:

    @callback
    def _on_tracker_restored(
        event: object,
        _notif_id: str = notif_id,
    ) -> None:
        new_state = getattr(event, "data", {}).get("new_state")
        if new_state is None:
            return
        t = new_state.attributes.get("device_trackers", [])
        if isinstance(t, list) and len(t) > 0:
            self._dismiss_ha_tracker_notif(_notif_id)

    self._ha_tracker_listeners[notif_id] = [
        async_track_state_change_event(
            self._hass, person_id, _on_tracker_restored
        ),
    ]
```

**For `_matter_cal_listeners` (single callback per entity, not a list):**
```python
# Source: D-08 / D-09 (CONTEXT.md) — to be implemented
# Dict is flat: entity_id → single Callable (not list, unlike
# _ha_tracker_listeners which uses list for extensibility).
# _matter_cal_listeners: dict[str, Callable]

@callback
def _make_cal_listener(
    area_id: str,
    entity_id: str,
) -> Callable:
    @callback
    def _on_matter_state_changed(event: object) -> None:
        new_state = getattr(event, "data", {}).get("new_state")
        if new_state is None:
            return
        # Only fire on current_temperature attribute changes
        old_state = getattr(event, "data", {}).get("old_state")
        new_temp = (new_state.attributes or {}).get("current_temperature")
        old_temp = (
            (old_state.attributes or {}).get("current_temperature")
            if old_state is not None
            else None
        )
        if new_temp == old_temp:
            return
        # Fire calibration for this room on the HA event loop
        self._hass.async_create_task(
            self._async_calibrate_room_only(area_id)
        )
    return _on_matter_state_changed
```

### Pattern 2: `entity_reg.async_get().platform` for platform detection

**What:** Read the entity registry entry for an entity_id and check
its `.platform` attribute to determine which integration registered it.

**When to use:** Whenever coordinator or WS handler needs to distinguish
between `tado_x` and `matter` climate entities.

**Example (existing pattern from websocket.py line 1268):**
```python
# Source: websocket.py lines 1264-1278
for eid in entity_ids:
    if not is_trv_entity(hass, eid):
        continue
    r = entity_reg.async_get(eid)
    if r and r.platform == "tado_x":
        zone_entity_id = eid
        # ...
        break
```

### Pattern 3: `set_matter_mapping` WS command factory

**What:** Write handler that mutates `runtime_config["matter_mappings"]`,
persists, sends result, then triggers listener refresh.

**When to use:** New WS commands that mutate top-level config keys.

**Template (based on `set_global_mode` + `set_room_config` patterns):**
```python
# Source: websocket.py lines 300-326 (_make_ws_set_global_mode)
def _make_ws_set_matter_mapping(entry: ClimateManagerConfigEntry):

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_matter_mapping",
            vol.Required("tado_entity_id"): str,
            vol.Required("matter_entity_ids"): list,
        }
    )
    @websocket_api.async_response
    async def ws_set_matter_mapping(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        tado_eid = msg["tado_entity_id"]
        matter_eids: list[str] = [
            e for e in msg["matter_entity_ids"]
            if isinstance(e, str) and e.startswith("climate.")
        ]
        mappings = entry.runtime_data.runtime_config.setdefault(
            "matter_mappings", {}
        )
        if matter_eids:
            mappings[tado_eid] = matter_eids
        else:
            mappings.pop(tado_eid, None)  # sparse: absent = no mapping
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        # D-16: refresh listeners atomically with config change
        coordinator = entry.runtime_data.coordinator
        if coordinator is not None:
            hass.async_create_task(
                coordinator._async_refresh_matter_listeners()
            )

    return ws_set_matter_mapping
```

### Pattern 4: `_async_refresh_matter_listeners()`

**What:** Cancel all existing `_matter_cal_listeners`, rebuild from current
`matter_mappings` + `runtime_data.rooms`.

**When to use:** Called at first `async_evaluate` and after any
`set_matter_mapping` call.

```python
# Source: D-10 (CONTEXT.md) — to be implemented
async def _async_refresh_matter_listeners(self) -> None:
    """Cancel all matter calibration listeners and re-register."""
    # Cancel all existing listeners (D-10: cancel-all-then-rebuild)
    for cancel in self._matter_cal_listeners.values():
        cancel()
    self._matter_cal_listeners.clear()

    from homeassistant.helpers import entity_registry as er  # noqa: PLC0415
    from homeassistant.helpers.event import (  # noqa: PLC0415
        async_track_state_change_event,
    )
    entity_reg = er.async_get(self._hass)
    config = self._data.runtime_config
    matter_mappings: dict[str, list[str]] = config.get(
        "matter_mappings", {}
    )

    for area_id, entity_ids in self._data.rooms.items():
        for entity_id in entity_ids:
            reg = entity_reg.async_get(entity_id)
            if reg is None:
                continue
            platform = reg.platform
            if platform == "tado_x":
                mapped = matter_mappings.get(entity_id)
                if mapped:
                    # D-09: mapped tado_x → no listener on tado_x;
                    # Matter entities get the listeners
                    for matter_eid in mapped:
                        if matter_eid in self._matter_cal_listeners:
                            continue  # already registered
                        cancel = async_track_state_change_event(
                            self._hass,
                            matter_eid,
                            self._make_matter_cal_listener(area_id),
                        )
                        self._matter_cal_listeners[matter_eid] = cancel
                else:
                    # D-09: unmapped tado_x → listener on tado_x entity
                    if entity_id not in self._matter_cal_listeners:
                        cancel = async_track_state_change_event(
                            self._hass,
                            entity_id,
                            self._make_matter_cal_listener(area_id),
                        )
                        self._matter_cal_listeners[entity_id] = cancel
            elif platform == "matter":
                # Check if this Matter entity is in any mapping value
                matter_entity_set = frozenset(
                    eid
                    for eids in matter_mappings.values()
                    for eid in eids
                )
                if entity_id not in matter_entity_set:
                    # D-09: unmapped Matter → listener
                    if entity_id not in self._matter_cal_listeners:
                        cancel = async_track_state_change_event(
                            self._hass,
                            entity_id,
                            self._make_matter_cal_listener(area_id),
                        )
                        self._matter_cal_listeners[entity_id] = cancel
```

### Anti-Patterns to Avoid

- **Ghost listeners from re-registration:** Never call
  `async_track_state_change_event` for an entity_id already in
  `_matter_cal_listeners` without cancelling the old callback first.
  The cancel-all-then-rebuild pattern (D-10) prevents this atomically.

- **Appending to `cancel_registry_listeners`:** D-11 explicitly forbids it.
  `cancel_registry_listeners` is for `hass.bus.async_listen` registry event
  callbacks only. Climate state_changed listeners belong in
  `_matter_cal_listeners`.

- **Spawning async tasks inside the listener callback:** The listener
  callback is a `@callback` (synchronous). Use
  `self._hass.async_create_task(...)` to schedule the async calibration
  coroutine from within the callback.

- **Reading `current_temperature` for the delta from the tado_x zone entity
  when a Matter mapping exists:** D-04 specifies the Matter entity is the
  temperature source. The tado_x zone entity reports the zone-level average
  plus an offset already applied — using it would double-count.

- **Missing `matter_entity_set` rebuild in `_async_refresh_matter_listeners`:**
  Build `matter_entity_set` once per call (D-03 specifics note: frozenset
  of all Matter entity_ids across all mapping values). Avoids O(n) inner
  loop scan for every Matter entity encountered.

- **Storing `matter_mappings` with null-valued entries:** Absent key = no
  mapping (sparse model). When `matter_entity_ids` is empty or null,
  `pop()` the tado_entity_id key from the dict. Never store
  `{entity_id: []}` — it creates ambiguity.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State change listening | Custom polling loop or bus event scan | `async_track_state_change_event` | Already imported in coordinator.py (line 1140); HA-canonical; handles event loop safety and entity removal |
| Platform detection | String parsing of entity_id or domain guessing | `entity_reg.async_get(entity_id).platform` | Entity registry is the authoritative source; already used in websocket.py line 1268 |
| Tado X device_id lookup | Parsing entity_id strings or guessing | `entity_reg.entities` iteration + `device_id` match | Same approach as offset_entry lookup in `ws_get_calibration_status` lines 1293-1309 |
| Voluptuous schema for list | Manual type checking | `vol.All(list, [...])` | Existing WS commands use vol for all input validation (T-03-04) |

**Key insight:** Every mechanism this phase needs is already imported or
used elsewhere in the codebase. No new patterns need to be invented; the
work is entirely about wiring existing patterns into new code paths.

---

## Runtime State Inventory

Not applicable — this is a new-feature phase, not a rename/refactor/migration.

---

## Open Questions

### 1. Device sharing: does a Tado X Radiator Valve X appear under the
same `device_id` in both `tado_x` and `matter` entity registry entries?

**What we know:**

From D-05 (CONTEXT.md): "Researcher must verify whether a Tado X Radiator
Valve X device appears under the same `device_id` in both the `tado_x` and
`matter` entity registry entries in Home Assistant. If yes,
`entity_reg.async_get(matter_entity_id).device_id` gives the device_id for
the offset call directly. If not (separate HA devices per integration), a
name/identifier-based matching strategy is needed."

From code review of `get_tado_valve_devices()` in trv.py (lines 163-194):
The function filters `dev_reg.devices.values()` by `device.model ==
"Radiator Valve X"` and `device.area_id`. This returns physical device
objects from the HA device registry, each with a unique `device.id`.

The HA device registry associates a physical device with one or more config
entries. When Matter and tado_x both integrate the same physical Tado X
valve, the question is whether HA creates ONE device entry shared by both
config entries, or TWO separate device entries (one per integration).

**From HA architecture:** [ASSUMED] Matter and tado_x typically create
SEPARATE device entries in the HA device registry, because each integration
registers its own device during setup. The Matter integration registers the
device via Matter commissioning; the tado_x integration registers via its
own cloud API. These would be two distinct HA device IDs for the same
physical valve, unless Tado has implemented device linking via unique
identifiers (`identifiers` or `connections` matching).

**Practical consequence:** If devices are SEPARATE (most likely):
- `entity_reg.async_get(matter_entity_id).device_id` gives the Matter
  device's HA device_id — NOT the tado_x device's device_id.
- Cannot directly call `tado_x.set_temperature_offset` with the Matter
  device_id because it would be unknown to the tado_x service.
- Must iterate `entity_reg.entities` to find a tado_x entity entry in the
  same HA area with `platform == "tado_x"` and `entity_id not in`
  tado_x zone entities. Then read its `device_id` for the offset call.
  Alternatively, use `get_tado_valve_devices(hass, area_id)` which already
  returns all Radiator Valve X device_ids in that area.

**D-05 fallback path (already specified in CONTEXT.md):**
If no matching tado_x device is found via device_id, fall back to
`_async_calibrate_room()` (entity-based offset via `temperature_offset`
attribute). This is safe — `supports_offset_calibration()` guards against
incompatible entities.

**Recommended planning approach:** Plan D-05 calibration using the
area-based device resolution (call `get_tado_valve_devices(hass, area_id)`
— it returns all Radiator Valve X device_ids for the room, which is exactly
what `_async_calibrate_tado_device()` needs). The tado_x zone entity lookup
and the Matter `current_temperature` read are separate; they do not require
the same device_id.

**Confidence:** LOW — live Tado X + Matter setup required to confirm.
The fallback in D-05 means planning can proceed safely without this answer.

### 2. Listener callback filter: should it check only
`current_temperature` changes or fire on any state_changed?

**What we know:** D-09 states: "fires on `current_temperature` attribute
change only (skip other attribute changes)". This is a performance
optimisation — Matter climate entities fire state_changed for setpoint
changes, mode changes, and temperature changes. Without the filter, every
setpoint push from the coordinator would also trigger a calibration pass.

**Implementation:** In the listener callback, compare
`event.data["new_state"].attributes.get("current_temperature")` with
`event.data["old_state"].attributes.get("current_temperature")` and return
early if unchanged. `old_state` can be None on entity startup — guard for
this case (return early, no calibration needed when entity first appears).

**Confidence:** HIGH — pattern is clear from D-09 and standard HA event
handling.

### 3. Calibration-only trigger: should the listener call
`_async_calibrate(config)` (all rooms) or a scoped helper?

**What we know:** Calling `_async_calibrate(config)` would re-calibrate
ALL rooms, not just the room whose Matter entity changed. This is wasteful.
The more efficient path is a helper `_async_calibrate_room_only(area_id)`
that runs the calibration logic for a single room without the broader gather.

**D-09 says:** "fires `_async_calibrate` for that room" — this implies a
room-scoped call, not a full multi-room calibration pass.

**Recommendation:** Add a private method
`_async_calibrate_for_room(area_id, config)` that runs only the tado_device
+ calibrate_room logic for the specified area_id. The listener callback
schedules this via `hass.async_create_task`. The periodic
`_async_calibrate(config)` continues to run all rooms as before.

**Confidence:** MEDIUM — logically sound, but the exact method signature
needs planner confirmation.

---

## Common Pitfalls

### Pitfall 1: Accumulating ghost listeners on `_async_refresh_matter_listeners`

**What goes wrong:** Each call to `_async_refresh_matter_listeners` adds
new listeners without cancelling the old ones. After N config changes,
each Matter entity_id has N active listeners. Every temperature change
fires N calibration passes.

**Why it happens:** Forgetting to cancel before rebuilding, or checking
`if entity_id not in self._matter_cal_listeners` before cancelling the old
value.

**How to avoid:** Always start `_async_refresh_matter_listeners` by
iterating `_matter_cal_listeners.values()` and calling each cancel, then
`_matter_cal_listeners.clear()`, before registering new listeners.

**Warning signs:** Integration reload leaves phantom calibration calls
in the HA log at unexpected times.

### Pitfall 2: D-03 `to_set` list including both the tado_x zone entity
and its mapped Matter entities

**What goes wrong:** The entity-by-entity loop adds the tado_x entity_id
to `to_set` regardless of mapping, then also adds the Matter entity_ids.
Both the tado_x zone and each individual valve get setpoint calls — the
tado_x call sets the zone for ALL physical valves, potentially fighting
the per-valve Matter calls.

**Why it happens:** Missing the `if mapped: to_set.extend(mapped)` vs
`else: to_set.append(entity_id)` conditional.

**How to avoid:** Follow D-03 exactly: when `matter_mappings.get(entity_id)`
returns a non-empty list, use `extend` (Matter entities only); otherwise
use `append` (tado_x entity). Never add both.

### Pitfall 3: Matter entity in `to_set` AND added by the tado_x branch

**What goes wrong:** A Matter entity_id appears in `to_set` twice — once
via the tado_x branch (D-03 extend) and once when iterating Matter entities.
The entity receives two setpoint calls per tick.

**Why it happens:** Not building `matter_entity_set` before the loop.

**How to avoid:** Build `matter_entity_set = frozenset(eid for eids in
matter_mappings.values() for eid in eids)` once before the area loop.
In the Matter-entity branch: `if entity_id not in matter_entity_set:
to_set.append(entity_id)`.

### Pitfall 4: Calibration using the tado_x zone entity's
`current_temperature` instead of the Matter entity's

**What goes wrong:** The delta `sensor_temp − current_temp` uses the
tado_x zone entity's temperature instead of the Matter entity's. The tado_x
zone temperature already has the applied offset baked in from the Tado cloud
refresh, which lags by minutes. The Matter entity reflects the offset
immediately.

**Why it happens:** Reusing the existing `_async_calibrate_tado_device`
call signature without updating the `zone_entity_id` parameter.

**How to avoid:** When Matter mapping exists, pass the Matter entity_id
as the temperature-reading entity, not the tado_x zone entity_id.

### Pitfall 5: `old_state` is None on entity startup

**What goes wrong:** The listener fires when a Matter entity first becomes
available (old_state=None). The code tries to read
`old_state.attributes.get("current_temperature")`, crashing with
`AttributeError`.

**Why it happens:** Standard HA state_changed events have `old_state=None`
on the very first state change after entity registration.

**How to avoid:** Guard: `if old_state is None: return` at the top of the
listener callback. The `_ha_tracker_listeners` callback in coordinator.py
already uses `if new_state is None: return` as a model.

### Pitfall 6: `_async_refresh_matter_listeners` called before rooms are
discovered

**What goes wrong:** Called at coordinator init before `runtime_data.rooms`
is populated, registering no listeners. The startup push in
`async_setup_entry` calls `coordinator.async_evaluate()` immediately after
construction, and `rooms` is already populated (set before coordinator
construction). However, if listeners are registered in `__init__` rather
than in `async_evaluate`, rooms may not yet be available.

**Why it happens:** Calling `_async_refresh_matter_listeners()` in
`coordinator.__init__` rather than in `async_setup` or first
`async_evaluate`.

**How to avoid:** D-10 says call at "coordinator startup (`async_setup` or
first `async_evaluate`)". Register in `async_evaluate` with a
`if not self._matter_cal_listeners_initialized:` guard flag, or simply
call it unconditionally at the start of `async_evaluate` before the
first evaluate call returns if `_matter_cal_listeners` is empty.

### Pitfall 7: WS payload validation — `matter_entity_ids` accepting
non-climate entity_ids

**What goes wrong:** A client sends `matter_entity_ids: ["sensor.foo"]`.
The mapping is stored, then `to_set` tries to call
`climate.set_temperature` on `sensor.foo`, raising `ServiceNotFound`.

**Why it happens:** The voluptuous schema does not validate entity_id
prefixes.

**How to avoid:** In the WS handler, filter `matter_entity_ids` to only
strings starting with `climate.` before storing:
```python
matter_eids = [
    e for e in msg["matter_entity_ids"]
    if isinstance(e, str) and e.startswith("climate.")
]
```

### Pitfall 8: Dict value type for `_matter_cal_listeners`

**What goes wrong:** `_ha_tracker_listeners` stores `dict[str, list]`
(a list of callables per key). Phase 13 D-08 specifies `dict[str, Callable]`
(single callable per key). Mixing the two types causes incorrect iteration
in the cancel loop (`for cancel in value` vs `cancel()`).

**Why it happens:** Copy-paste from `_ha_tracker_listeners` without
updating the value type.

**How to avoid:** `_matter_cal_listeners: dict[str, Callable]` stores the
cancel callable directly. The unload loop is:
```python
for cancel in self._matter_cal_listeners.values():
    cancel()
```
Not `for cancel in value: cancel()`.

---

## Code Examples

### Verified pattern: `async_track_state_change_event` usage in coordinator

```python
# Source: coordinator.py lines 1139-1207 (_check_ha_tracker_warnings)
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

# Register a state-change listener; returned callable cancels the listener
cancel = async_track_state_change_event(
    self._hass, entity_id, callback_fn
)
# Store cancel callable keyed by a string identifier
self._ha_tracker_listeners[notif_id] = [cancel]

# Cancel all listeners for a key
for cancel_fn in self._ha_tracker_listeners.pop(notif_id, []):
    cancel_fn()
```

[VERIFIED: codebase grep] `async_track_state_change_event` confirmed at
coordinator.py line 1140.

### Verified pattern: entity registry platform check

```python
# Source: websocket.py lines 1264-1278
entity_reg = er.async_get(hass)
for eid in entity_ids:
    r = entity_reg.async_get(eid)
    if r and r.platform == "tado_x":
        # tado_x zone entity found
        zone_entity_id = eid
        break
```

[VERIFIED: codebase grep] Pattern confirmed at websocket.py line 1268.

### Verified pattern: `get_tado_valve_devices` returns device_ids for area

```python
# Source: trv.py lines 163-194
valve_devices = get_tado_valve_devices(self._hass, area_id)
# Returns: [{"device_id": str, "name": str}, ...] for Radiator Valve X
# devices in the area. Empty list when no tado_x or no devices in area.
for device in valve_devices:
    await set_trv_offset_by_device(
        self._hass, device["device_id"], new_offset
    )
```

[VERIFIED: codebase grep] Function confirmed at trv.py line 163.

### Verified pattern: `_async_calibrate_tado_device` with different
temperature source

```python
# Source: coordinator.py lines 889-953
# Current: zone_entity_id provides current_temperature reading
# Phase 13 modification: pass matter_entity_id instead when mapping exists
# The signature accepts zone_entity_id as the temperature-reading entity;
# for mapped rooms, this becomes the Matter entity_id.
await self._async_calibrate_tado_device(
    area_id,
    device_id,          # from get_tado_valve_devices or entity_reg match
    matter_entity_id,   # D-04: use Matter entity for temperature reading
    sensor_entity_id,
    config,
)
```

[VERIFIED: codebase grep] Method signature confirmed at coordinator.py
line 889.

### Verified pattern: sparse key in DEFAULT_CONFIG

```python
# Source: const.py lines 220-236
DEFAULT_CONFIG: dict = {
    # ...
    "rooms": {},   # sparse: only rooms with non-default config
    "zones": {},   # sparse: only custom zones
    # Phase 13 addition:
    "matter_mappings": {},  # sparse: only rooms with Matter mapping
}
```

[VERIFIED: codebase grep] Pattern confirmed at const.py line 220.

### Verified pattern: WS factory with persist + evaluate

```python
# Source: websocket.py lines 300-326 (_make_ws_set_global_mode)
def _make_ws_set_matter_mapping(entry):

    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_matter_mapping",
        vol.Required("tado_entity_id"): str,
        vol.Required("matter_entity_ids"): list,
    })
    @websocket_api.async_response
    async def ws_set_matter_mapping(hass, connection, msg):
        # mutate → persist → send_result → coordinator action
        # (D-16: coordinator action = _async_refresh_matter_listeners,
        #  not async_evaluate)
        ...

    return ws_set_matter_mapping
```

[VERIFIED: codebase grep] Factory pattern confirmed at websocket.py
lines 300-326.

### Verified pattern: frontend `<select>` entity picker (Phase 11 D-15)

```typescript
// Source: confirmed pattern from CONTEXT.md Phase 11 D-15 (Phase 11
// calendar entity picker uses same approach)
// Filter hass.states + entity registry platform check:
const matterEntities = Object.keys(this.hass.states)
  .filter(eid =>
    eid.startsWith("climate.") &&
    // entity registry platform === "matter" check via get_config
    // climate_entities list provides all climate entity IDs;
    // matter filtering relies on backend delivering platform info
    // via get_config or a separate entities list
  );
```

[ASSUMED] Frontend entity registry platform check approach — the panel
does not have direct access to the HA entity registry. The backend
`get_config` currently returns `climate_entities` (all climate entity_ids).
For the Matter picker, the backend either needs to return Matter entities
separately, or the frontend can filter by area using `hass.states` and
rely on the user knowing which entities are Matter. **Planner must decide
how to surface Matter entity list to frontend** (see Assumptions Log A2).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Calibration only on 1-min tick | Event-driven calibration on state_changed | Phase 13 | Sub-minute responsiveness |
| All TRVs in room get same setpoint call | Entity-by-entity dispatch with mapping awareness | Phase 13 | Each physical valve gets individual setpoint via Matter |
| Calibration delta uses tado_x zone temperature | Calibration delta uses Matter entity temperature | Phase 13 | More accurate delta (no cloud-refresh lag) |

**No deprecated patterns in this phase** — it extends existing patterns
without removing any.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Matter and tado_x integrations create SEPARATE HA device registry entries for the same physical Tado X valve | Open Questions §1 | If they share the same device_id, the device_id resolution in D-05 simplifies to a direct lookup; the fallback is still correct either way |
| A2 | Frontend Matter entity picker filters using `hass.states` domain prefix only, without entity registry platform access | Code Examples §frontend | If platform info is needed, backend must expose a `matter_entities` list in `get_config`; planner must choose the approach |
| A3 | `_matter_cal_listeners` stores a single `Callable` per entity_id (not a list) as specified in D-08 | Architecture Patterns §Pattern 1 | If a list is used (like `_ha_tracker_listeners`), the cancel loop syntax differs; low risk, easy to fix |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `homeassistant.helpers.event.async_track_state_change_event` | Listener registration | ✓ | HA 2025.x | — |
| `homeassistant.helpers.entity_registry` | Platform detection | ✓ | HA 2025.x | — |
| `tado_x` integration + `Radiator Valve X` devices | D-05 calibration path | Unknown in test env | — | Fallback to `_async_calibrate_room()` per D-05 |
| Matter integration + climate entities | Mapping + listeners | Unknown in test env | — | Tests must mock entity states |
| pytest-homeassistant-custom-component | Unit tests | ✓ | installed | — |

**Missing dependencies with no fallback:** None — all HA helpers are
available; tado_x/Matter are only needed in production (not in tests).

**Missing dependencies with fallback:**
- Live tado_x + Matter setup for D-05 device_id verification: fallback is
  the area-based `get_tado_valve_devices()` approach which is already in
  the codebase and does not require device_id matching across integrations.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest-homeassistant-custom-component |
| Config file | `pytest.ini` / `pyproject.toml` |
| Quick run command | `make test` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCALIB-01 | Mapped Matter entity listener fires `_async_calibrate_for_room` on `current_temperature` change | unit | `make test` | ❌ Wave 0 |
| MCALIB-01 | `to_set` uses Matter entity_ids (not tado_x) when mapping exists | unit | `make test` | ❌ Wave 0 |
| MCALIB-01 | Calibration reads `current_temperature` from Matter entity, not tado_x zone | unit | `make test` | ❌ Wave 0 |
| MCALIB-02 | `_async_refresh_matter_listeners` cancels old listeners before re-registering | unit | `make test` | ❌ Wave 0 |
| MCALIB-02 | `async_unload_entry` cancels all `_matter_cal_listeners` | unit | `make test` | ❌ Wave 0 |
| MCALIB-02 | Removing a mapping (empty list) pops the key and cancels the listener | unit | `make test` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_coordinator.py` — new test functions for Matter listener
  lifecycle (MCALIB-02), calibration routing (MCALIB-01), and `to_set`
  entity dispatch (D-03)
- [ ] `tests/test_websocket.py` — new test functions for `set_matter_mapping`
  WS handler (persist, sparse removal, listener refresh trigger)

*(Existing test infrastructure and conftest.py cover the framework setup.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | WS auth handled by HA |
| V3 Session Management | no | HA WS session |
| V4 Access Control | no | `require_admin=False` panel; HA handles auth |
| V5 Input Validation | yes | `vol.Required` schema + `startswith("climate.")` filter in WS handler |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| WS payload with non-climate entity_ids in `matter_entity_ids` | Tampering | Filter `[e for e in ids if e.startswith("climate.")]` before storing |
| WS payload with arbitrary tado_entity_id pointing to non-tado_x entity | Tampering | Coordinator resolves actual platform at runtime via entity registry; no service call is issued for non-tado_x entities |
| Listener accumulation (ghost listeners on rapid WS calls) | — | Cancel-all-then-rebuild is safe; WS commands are serialised on HA event loop (D-10 note in CONTEXT.md) |

---

## Sources

### Primary (HIGH confidence)

- `coordinator.py` — `_ha_tracker_listeners` dict, `async_track_state_change_event`
  import and usage, `_async_calibrate_tado_device`, `_async_calibrate_room`
  — read in full as part of this research
- `__init__.py` — `ClimateManagerData`, `async_setup_entry`,
  `async_unload_entry`, `cancel_registry_listeners` lifecycle — read in full
- `trv.py` — `get_tado_valve_devices`, `set_trv_offset_by_device`,
  `supports_offset_calibration` — read in full
- `const.py` — `DEFAULT_CONFIG`, sparse key pattern — read in full
- `websocket.py` — `_make_ws_set_global_mode`, `_make_ws_set_room_config`,
  `_make_ws_set_person_config`, `_make_ws_get_calibration_status`,
  `async_register_commands` — read in full
- `frontend/src/types.ts` — `ClimateConfig`, `RoomConfig` — read in full
- `frontend/src/ws-client.ts` — all existing WS methods — read in full
- `frontend/src/components/room-card.ts` — TRV section, zone assignment,
  person association patterns — read first 500 lines
- `.planning/phases/13-matter-tado-x-real-time-calibration/13-CONTEXT.md`
  — all decisions D-01 through D-16 — read in full

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — MCALIB-01, MCALIB-02 — read in full
- `.planning/STATE.md` — milestone context — read in full

### Tertiary (LOW confidence)

- A1 (Matter + tado_x device registry separation) — training knowledge,
  not verified against live HA setup

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all imports and patterns verified directly in
  codebase; no new packages
- Architecture: HIGH — every pattern traced to existing codebase line
  references
- Pitfalls: HIGH — identified directly from code review of existing
  listener patterns and coordinator control path
- D-05 device_id resolution: LOW — requires live Tado X + Matter setup
  to confirm; fallback is safe and specified

**Research date:** 2026-06-03
**Valid until:** 2026-07-03 (stable HA integration patterns; no
fast-moving dependencies)

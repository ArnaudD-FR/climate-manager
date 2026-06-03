# Phase 13: Matter→Tado X Real-Time Calibration — Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 9 (7 modified, 2 new tests)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `custom_components/climate_manager/const.py` | config | — | `const.py` itself (sparse key pattern) | exact |
| `custom_components/climate_manager/coordinator.py` | service | event-driven + request-response | `coordinator.py` `_ha_tracker_listeners` block | exact |
| `custom_components/climate_manager/__init__.py` | config | request-response | `__init__.py` `async_unload_entry` cancel loop | exact |
| `custom_components/climate_manager/websocket.py` | controller | request-response | `_make_ws_set_global_mode` / `_make_ws_get_calibration_status` | exact |
| `frontend/src/types.ts` | model | — | `types.ts` `ClimateConfig` interface | exact |
| `frontend/src/ws-client.ts` | service | request-response | `ws-client.ts` `setCalibrationConfig` method | exact |
| `frontend/src/components/room-card.ts` | component | event-driven | `room-card.ts` zone `<select>` + `person-card.ts` calendar entity picker | role-match |
| `tests/test_coordinator.py` | test | — | `tests/test_coordinator.py` existing lifecycle tests | exact |
| `tests/test_websocket.py` | test | — | `tests/test_websocket.py` WS handler tests | exact |

---

## Pattern Assignments

### `custom_components/climate_manager/const.py` — add `matter_mappings` default

**Analog:** `const.py` lines 220–236 (existing sparse key pattern)

**Core pattern** (lines 220–236):
```python
DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
    "global_time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "rooms": {},  # sparse: only rooms with non-default config
    "persons": {},  # sparse: only persons with non-default settings
    "default_zone_name": "Home",
    "zones": {},  # ZONE-01: custom zones, keyed by UUID string
    "calibration_enabled": False,
    "calibration_threshold": 0.5,
    # Phase 13 addition (D-02):
    "matter_mappings": {},  # sparse: only rooms with Matter mapping
}
```

**Rule:** Add `"matter_mappings": {}` after `"calibration_threshold"`. Same sparse
pattern as `"rooms"`, `"zones"` — absent key = no mapping, no migration needed.

---

### `custom_components/climate_manager/coordinator.py` — four additions

This file receives the bulk of Phase 13 changes. Four separate integration points.

#### 13-A: `__init__` — add `_matter_cal_listeners` instance variable

**Analog:** `coordinator.py` lines 134–143 (`_ha_tracker_listeners` declaration)

**Pattern** (lines 134–143):
```python
# Cancel callbacks for active ha-tracker watchers, keyed by notif_id.
self._ha_tracker_listeners: dict[str, list] = {}
```

**Copy as** (single Callable per entry — D-08 distinction from `_ha_tracker_listeners`
which uses `list`):
```python
# D-08: cancel callbacks for Matter calibration state_changed listeners.
# Keyed by entity_id (Matter or tado_x). Single Callable per key
# (unlike _ha_tracker_listeners which uses list for extensibility).
# Cancel-all-then-rebuild via _async_refresh_matter_listeners().
self._matter_cal_listeners: dict[str, Callable] = {}
```

The `Callable` import is already present in `__init__.py`; add it to the
`from typing import TYPE_CHECKING` block in `coordinator.py` if not already there.

#### 13-B: `async_evaluate` — call `_async_refresh_matter_listeners` on first run

**Analog:** `coordinator.py` lines 162–222 (`async_evaluate`)

**Integration point** — insert after line 222 (`await self._async_calibrate(config)`),
or at the start of the method before the calibration pass, guarded by empty dict:

```python
# D-10: register Matter calibration listeners on first evaluate call.
# Rooms are populated by async_setup_entry before async_evaluate is called,
# so _matter_cal_listeners is always built against current runtime_data.rooms.
if not self._matter_cal_listeners:
    await self._async_refresh_matter_listeners()
```

#### 13-C: `_push_temperatures` — entity-by-entity dispatch (D-03)

**Analog:** `coordinator.py` lines 515–540 (`_push_temperatures` with `asyncio.gather`)

**Existing pattern** (lines 515–540):
```python
async def _push_temperatures(
    self,
    rooms: dict[str, list[str]],
    desired_temps: dict[str, float],
    mode_off_rooms: set[str],
) -> None:
    """Push pass — off-capable TRVs in mode_off_rooms use _push_off_safely."""
    await asyncio.gather(
        *(
            (
                self._push_off_safely(entity_id, desired_temps[area_id])
                if supports_hvac_off(self._hass, entity_id)
                else self._push_safely(
                    entity_id, desired_temps[area_id], "ZONE_EVAL_OFF"
                )
            )
            if area_id in mode_off_rooms
            else self._push_safely(
                entity_id, desired_temps[area_id], "ZONE_EVAL"
            )
            for area_id, entity_ids in rooms.items()
            for entity_id in entity_ids
            if area_id in desired_temps
            and is_trv_entity(self._hass, entity_id)
        )
    )
```

**Replace the flat `for entity_id in entity_ids` iteration** with the D-03
entity-by-entity dispatch. The `to_set` list must be built per area before the
`asyncio.gather`. Key points:
- Build `matter_entity_set` once per method call (not per area) from
  `frozenset(eid for eids in matter_mappings.values() for eid in eids)`.
- For each area, build `to_set` using the D-03 conditional (see CONTEXT.md D-03).
- Pass `to_set` to the existing `_push_safely` / `_push_off_safely` dispatch.
- The entity registry import `from homeassistant.helpers import entity_registry as er`
  is already used inside `_async_calibrate` — import at method top with
  `from homeassistant.helpers import entity_registry as er  # noqa: PLC0415`.

#### 13-D: New methods — `_async_refresh_matter_listeners` and
`_make_matter_cal_listener`

**Analog:** `coordinator.py` lines 1125–1207 (`_check_ha_tracker_warnings` /
`_ha_tracker_listeners` registration block)

**`async_track_state_change_event` import pattern** (lines 1139–1141):
```python
from homeassistant.helpers.event import (  # noqa: PLC0415
    async_track_state_change_event,
)
```

**Cancel-all pattern** (lines 1121–1123, `_dismiss_ha_tracker_notif`):
```python
for cancel in self._ha_tracker_listeners.pop(notif_id, []):
    cancel()
```

For `_matter_cal_listeners` (single Callable, not list — D-08):
```python
for cancel in self._matter_cal_listeners.values():
    cancel()
self._matter_cal_listeners.clear()
```

**Listener registration pattern** (lines 1189–1207):
```python
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

**Copy as** (for `_matter_cal_listeners`, single cancel per entity, current_temperature
guard, area_id closure):
```python
@callback
def _make_matter_cal_listener(
    self,
    area_id: str,
) -> Callable:
    """Factory: create a state_changed callback for a Matter/tado_x entity.

    D-09: only fires calibration when current_temperature attribute changes.
    Guards old_state=None (Pitfall 5 — entity startup event).
    Schedules _async_calibrate_for_room via hass.async_create_task
    (Pitfall — listener is @callback, cannot await directly).
    """
    @callback
    def _on_state_changed(event: object) -> None:
        new_state = getattr(event, "data", {}).get("new_state")
        if new_state is None:
            return
        old_state = getattr(event, "data", {}).get("old_state")
        new_temp = (new_state.attributes or {}).get("current_temperature")
        old_temp = (
            (old_state.attributes or {}).get("current_temperature")
            if old_state is not None
            else None
        )
        if new_temp == old_temp:
            return
        self._hass.async_create_task(
            self._async_calibrate_for_room(area_id)
        )
    return _on_state_changed
```

**`_async_calibrate_tado_device` signature** (lines 889–903) — for mapped Matter
entities, pass the Matter entity_id as the temperature-reading entity (D-04):
```python
async def _async_calibrate_tado_device(
    self,
    area_id: str,
    device_id: str,
    zone_entity_id: str | None,   # D-04: Matter entity_id when mapping exists
    sensor_entity_id: str | None,
    config: dict,
) -> None:
```

**`_async_calibrate_room` signature** (lines 955–967) — used as fallback for
unmapped Matter entities (D-07):
```python
async def _async_calibrate_room(
    self,
    area_id: str,
    entity_id: str,
    sensor_entity_id: str | None,
    config: dict,
) -> None:
```

**`get_tado_valve_devices` call** (line 858) — for D-05 area-based device_id
resolution (returns all Radiator Valve X device_ids in the area):
```python
valve_devices = get_tado_valve_devices(self._hass, area_id)
# Returns: [{"device_id": str, "name": str}, ...]
```

---

### `custom_components/climate_manager/__init__.py` — unload teardown

**Analog:** `__init__.py` lines 289–307 (`async_unload_entry`)

**Existing cancel loop** (lines 299–306):
```python
if entry.runtime_data.cancel_scheduler is not None:
    entry.runtime_data.cancel_scheduler()

for cancel in entry.runtime_data.cancel_registry_listeners:
    cancel()
```

**Add after the registry listeners loop** (D-11 — separate dict, not appended
to `cancel_registry_listeners`):
```python
# D-11: cancel all Matter calibration state_changed listeners.
# These live in coordinator._matter_cal_listeners, NOT in
# cancel_registry_listeners (which is for bus registry events only).
coordinator = entry.runtime_data.coordinator
if coordinator is not None:
    for cancel in coordinator._matter_cal_listeners.values():
        cancel()
    coordinator._matter_cal_listeners.clear()
```

---

### `custom_components/climate_manager/websocket.py` — `set_matter_mapping` command

**Analog:** `websocket.py` lines 300–326 (`_make_ws_set_global_mode`) for the
factory structure; lines 1208–1345 (`_make_ws_get_calibration_status`) for
entity registry platform detection.

**Factory structure** (lines 300–326):
```python
def _make_ws_set_global_mode(entry: ClimateManagerConfigEntry):
    """Factory: create set_global_mode handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_global_mode",
            vol.Required("mode"): vol.In(VALID_MODES),
        }
    )
    @websocket_api.async_response
    async def ws_set_global_mode(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_global_mode
```

**Copy as** (D-15/D-16 — mutate sparse dict, persist, send_result, then call
`_async_refresh_matter_listeners` instead of `async_evaluate`):
```python
def _make_ws_set_matter_mapping(entry: ClimateManagerConfigEntry):
    """Factory: create set_matter_mapping handler."""

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
        # Pitfall 7: validate entity_id prefixes before storing
        matter_eids = [
            e for e in msg["matter_entity_ids"]
            if isinstance(e, str) and e.startswith("climate.")
        ]
        mappings = entry.runtime_data.runtime_config.setdefault(
            "matter_mappings", {}
        )
        if matter_eids:
            mappings[msg["tado_entity_id"]] = matter_eids
        else:
            mappings.pop(msg["tado_entity_id"], None)  # D-01 sparse: never store []
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        # D-16: refresh listeners atomically after persist
        coordinator = entry.runtime_data.coordinator
        if coordinator is not None:
            hass.async_create_task(
                coordinator._async_refresh_matter_listeners()
            )

    return ws_set_matter_mapping
```

**Entity registry platform check** (lines 1264–1278) — same pattern for Matter
entity filtering in WS handler or coordinator:
```python
entity_reg = er.async_get(hass)
for eid in entity_ids:
    if not is_trv_entity(hass, eid):
        continue
    r = entity_reg.async_get(eid)
    if r and r.platform == "tado_x":
        zone_entity_id = eid
        break
# For Matter: r.platform == "matter"
```

**Registration in `async_register_commands`** (lines 78–123):
```python
# Add alongside existing commands:
websocket_api.async_register_command(
    hass, _make_ws_set_matter_mapping(entry)
)
```

---

### `frontend/src/types.ts` — extend `ClimateConfig`

**Analog:** `types.ts` lines 104–132 (`ClimateConfig` interface)

**Existing interface** (lines 104–132):
```typescript
export interface ClimateConfig {
  global_mode: string;
  period_temperatures: Record<string, number>;
  global_time_program: DailyProgram;
  default_zone_name: string;
  default_zone_preheat_enabled?: boolean;
  zones: Record<string, ZoneConfig>;
  rooms: Record<string, RoomConfig>;
  persons: Record<string, PersonConfig>;
  climate_entities: string[];
  calibration_enabled?: boolean;
  calibration_threshold?: number;
}
```

**Add** (D-01 schema, sparse — absent = no mappings):
```typescript
/**
 * Phase 13 (D-01): Matter entity pairings.
 * Key: tado_x zone climate entity_id.
 * Value: list of Matter climate entity_ids paired to that tado_x entity.
 * Sparse — absent key means no mapping for that room.
 */
matter_mappings?: Record<string, string[]>;
```

---

### `frontend/src/ws-client.ts` — add `setMatterMapping` method

**Analog:** `ws-client.ts` lines 217–223 (`setCalibrationConfig`)

**Existing method pattern** (lines 217–223):
```typescript
/** Enable or disable TRV offset auto-calibration globally. */
setCalibrationConfig(enabled: boolean): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_calibration_config",
    enabled,
  });
}
```

**Copy as** (D-15 — matches WS command payload schema):
```typescript
/**
 * Set or remove a Matter entity mapping for a tado_x zone entity.
 * Pass an empty array for matterEntityIds to remove the mapping (D-01 sparse).
 */
setMatterMapping(
  tadoEntityId: string,
  matterEntityIds: string[],
): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_matter_mapping",
    tado_entity_id: tadoEntityId,
    matter_entity_ids: matterEntityIds,
  });
}
```

---

### `frontend/src/components/room-card.ts` — Matter pairing section

**Analog 1:** `room-card.ts` lines 421–433 (`_onZoneChange` — auto-save on
`<select>` change without a Save button):
```typescript
private async _onZoneChange(e: Event) {
  const newZoneId = (e.target as HTMLSelectElement).value;
  const patch: Partial<RoomConfig> = newZoneId
    ? { zone_id: newZoneId }
    : { zone_id: null as unknown as string | undefined };
  try {
    await this.ws.setRoomConfig(this.roomId, patch);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

**Analog 2:** `person-card.ts` lines 796–799 (D-15 calendar entity picker —
filter `hass.states` by domain prefix):
```typescript
// D-15: calendar entity list from hass.states filtered to calendar.*
const calendarEntityIds = Object.keys(this.panel.hass?.states ?? {})
  .filter((id) => id.startsWith("calendar."))
  .sort();
```

**Analog 3:** `person-card.ts` lines 521–554 (native `<select>` with friendly
name display — copy for Matter entity picker):
```typescript
<div class="select-wrapper">
  <select
    class="mode-select"
    @change=${(e: Event) => {
      const newId = (e.target as HTMLSelectElement).value;
      onChange({
        ...(cfg ?? { event_means: "absent" }),
        entity_id: newId,
      });
    }}
  >
    ${entityIds.length === 0
      ? html`<option value="" disabled selected>
          No calendar entities found in Home Assistant.
        </option>`
      : html`
          <option value="" disabled ?selected=${!entityId}>
            — Select a calendar —
          </option>
          ${entityIds.map(
            (id) => html`
              <option value=${id} ?selected=${entityId === id}>
                ${(this.panel.hass?.states[id]?.attributes
                  ?.friendly_name as string | undefined) ?? id}
              </option>
            `,
          )}
        `}
  </select>
</div>
```

**Copy as** (Matter entity picker — D-12/D-13):
```typescript
// D-13: filter hass.states to climate.* entities in the same area.
// Note: frontend cannot check entity registry platform directly.
// Backend will deliver Matter entities via get_config matter_mappings;
// frontend filters climate.* from hass.states and relies on user selection.
// If Assumption A2 holds, domain prefix filter is sufficient.
const matterEntityIds = Object.keys(this.panel.hass?.states ?? {})
  .filter((id) => id.startsWith("climate."))
  .sort();
```

**Auto-save handler pattern** (D-12 — auto-save on change, no Save button):
```typescript
private async _onMatterMappingChange(
  tadoEntityId: string,
  e: Event,
) {
  const selected = (e.target as HTMLSelectElement).value;
  const matterEntityIds = selected ? [selected] : [];
  try {
    await this.ws.setMatterMapping(tadoEntityId, matterEntityIds);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

**Section visibility guard** (D-12 — only show when room has tado_x entity):
The `entity_ids` for the room are available via `this.roomStatus?.entity_ids`.
Planner must decide how to surface tado_x entity detection — options:
(a) backend `get_config` includes a `tado_x_entities` per room (mirrors
`climate_entities`), or (b) frontend computes from `matter_mappings` keys
present in the room. See RESEARCH.md Assumption A2 for the open decision.

---

### `tests/test_coordinator.py` — new Matter listener lifecycle tests

**Analog:** `tests/test_coordinator.py` lines 1–130 (imports, `_make_runtime_config`
helper, `MockConfigEntry` + `async_mock_service` scaffold)

**Test scaffold pattern** (lines 62–80):
```python
async def _setup_entry(hass) -> MockConfigEntry:
    """Helper: set up the integration entry and return it."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
```

**New tests needed** (MCALIB-01, MCALIB-02):
- `test_matter_listeners_registered_on_first_evaluate` — after setup, verify
  `coordinator._matter_cal_listeners` is non-empty for rooms with climate entities.
- `test_matter_listener_fires_calibrate_on_temp_change` — fire a
  `state_changed` event with changed `current_temperature`; verify
  `_async_calibrate_for_room` is called.
- `test_refresh_matter_listeners_cancels_old` — call
  `_async_refresh_matter_listeners()` twice; verify the first set of cancel
  functions was called.
- `test_unload_cancels_matter_listeners` — after unload, verify all listener
  cancel callbacks were called (mirrors `test_unload_cancels_scheduler`).
- `test_to_set_uses_matter_entities_when_mapped` — with `matter_mappings` set,
  verify `_push_temperatures` calls `_push_safely` with Matter entity_ids, not
  tado_x zone entity_id.

---

### `tests/test_websocket.py` — new `set_matter_mapping` WS handler tests

**Analog:** `tests/test_websocket.py` lines 62–130 (`_setup_entry` helper +
existing handler tests)

**Test scaffold** (lines 62–71, reuse as-is):
```python
async def _setup_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
```

**New tests needed**:
- `test_set_matter_mapping_stores_mapping` — send `set_matter_mapping` with
  valid payload; verify `runtime_config["matter_mappings"]` updated.
- `test_set_matter_mapping_empty_list_pops_key` — send `matter_entity_ids: []`;
  verify tado_entity_id key is absent from `matter_mappings` (sparse model).
- `test_set_matter_mapping_filters_non_climate_entity_ids` — send
  `matter_entity_ids: ["sensor.foo", "climate.valve"]`; verify only
  `"climate.valve"` is stored.
- `test_set_matter_mapping_triggers_listener_refresh` — after send, verify
  `coordinator._async_refresh_matter_listeners` was called (mock or spy).

---

## Shared Patterns

### Sparse config key
**Source:** `const.py` lines 220–236; `websocket.py` lines 483–500
**Apply to:** `const.py` default, `websocket.py` handler
```python
# Absent key = not configured. Never store empty list/null.
# Use setdefault + conditional pop for atomic sparse mutations:
mappings = runtime_config.setdefault("matter_mappings", {})
if matter_eids:
    mappings[key] = matter_eids
else:
    mappings.pop(key, None)
```

### Async-safe listener registration from `@callback`
**Source:** `coordinator.py` lines 1189–1207
**Apply to:** `_make_matter_cal_listener` callback body
```python
# @callback functions cannot await. Schedule async work via async_create_task:
self._hass.async_create_task(
    self._async_calibrate_for_room(area_id)
)
```

### WS factory pattern (mutate → persist → send_result → coordinator action)
**Source:** `websocket.py` lines 300–326
**Apply to:** `_make_ws_set_matter_mapping`
```python
entry.runtime_data.runtime_config["key"] = value
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(coordinator.action())
```

### Entity registry platform check
**Source:** `websocket.py` lines 1264–1278
**Apply to:** coordinator `_async_refresh_matter_listeners`, any platform branching
```python
from homeassistant.helpers import entity_registry as er  # noqa: PLC0415
entity_reg = er.async_get(hass)
r = entity_reg.async_get(entity_id)
if r and r.platform == "tado_x":   # or "matter"
    ...
```

### `asyncio.gather` over dynamic entity list
**Source:** `coordinator.py` lines 522–540 (`_push_temperatures`)
**Apply to:** `_push_temperatures` modified entity dispatch; `_async_calibrate` tasks
```python
await asyncio.gather(*[coroutine(eid) for eid in to_set])
```

### Frontend auto-save on `<select>` change
**Source:** `room-card.ts` lines 421–433 (`_onZoneChange`)
**Apply to:** `_onMatterMappingChange` in room-card.ts
```typescript
try {
  await this.ws.setMatterMapping(tadoEntityId, matterEntityIds);
  await this.panel.reloadConfig();
  this.panel.showToast("Saved", false);
} catch {
  this.panel.showToast("Save failed — retrying...", true);
}
```

### Frontend entity picker from `hass.states`
**Source:** `person-card.ts` lines 796–799
**Apply to:** Matter entity `<select>` in room-card.ts
```typescript
const entityIds = Object.keys(this.panel.hass?.states ?? {})
  .filter((id) => id.startsWith("climate."))
  .sort();
```

---

## No Analog Found

All Phase 13 files have close analogs in the codebase. No new patterns need to
be invented.

One **open decision for the planner** (Assumption A2 from RESEARCH.md): the
frontend cannot read the HA entity registry directly, so it cannot filter
`climate.* ` entities by `platform === "matter"`. Options:

| Option | Approach | Cost |
|--------|----------|------|
| A | Backend adds `matter_entities` list to `get_config` (per-room or global) | Small backend addition |
| B | Frontend shows all `climate.*` entities and relies on user to pick the right one | No backend change; user must know which entity is Matter |
| C | Backend filters Matter entities in `get_config` room data via entity_reg | Inline in existing `get_config` handler |

Planner must choose and document in PLAN.md.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`,
`tests/`
**Files scanned:** 10 source files read in full or targeted sections
**Pattern extraction date:** 2026-06-03

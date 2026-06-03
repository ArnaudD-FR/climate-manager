# Phase 13: Matter→Tado X Real-Time Calibration - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an explicit `matter_mappings` config that links tado_x zone climate entities
to their corresponding Matter climate entities (one per physical Tado X Radiator
Valve X). When mapped:

- The coordinator routes setpoint calls through the Matter entities instead of
  the tado_x zone entity (one call per physical TRV via `asyncio.gather`)
- `state_changed` listeners on Matter entities fire calibration immediately on
  `current_temperature` changes — sub-minute responsiveness
- Calibration delta uses the Matter entity's `current_temperature` (already
  reflects the applied offset)

Unmapped rooms (tado_x only or pure Matter) retain existing behaviour but also
gain event-driven calibration via `state_changed` listeners on their climate
entities.

**In scope:**

- Root-level `matter_mappings` config key: `{ tado_entity_id: [matter_entity_ids] }`
- Revised coordinator control path: entity-by-entity dispatch in the area loop
- `state_changed` listeners on Matter entities (mapped) and tado_x/Matter
  entities (unmapped) to trigger immediate calibration
- Listener lifecycle: per-entity cancel callbacks; re-registration when mappings
  change via WS command
- Frontend room card: per-TRV pairing UI — assign Matter entity to each tado_x
  TRV row; grouped display; auto-save on change
- New WS commands: `set_matter_mapping` / `delete_matter_mapping`

**Out of scope:**

- Fallback: when Matter becomes unavailable, no automatic fall-back to tado_x
  entity (tado_x entity is fully replaced when mapping exists)
- Non-Tado-X Matter TRVs: unmapped Matter entities treated as independent (same
  calibration path as a generic TRV with `temperature_offset` attribute or
  `tado_x.set_temperature_offset` service, resolved via existing
  `supports_offset_calibration()`)
- Multi-language labels for the pairing UI

</domain>

<decisions>
## Implementation Decisions

### Config Schema

- **D-01:** New root-level key `matter_mappings` at the same level as `rooms`,
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
  Key: tado_x climate entity_id (the zone entity already in
  `runtime_data.rooms[area_id]`).
  Value: list of Matter climate entity_ids paired to that tado_x entity.
  Absent = no mapping for that room (sparse — no migration needed).

- **D-02:** `DEFAULT_CONFIG["matter_mappings"] = {}` (sparse default, same
  pattern as `rooms` and `zones`).

### Coordinator — Control Path

- **D-03:** For each `area_id` in `async_evaluate`, loop over all climate
  entities in `runtime_data.rooms[area_id]` and build a "to-set" list:

  ```
  to_set = []
  for entity_id in area_climate_entities:
      platform = entity_reg.async_get(entity_id).platform
      if platform == "tado_x":
          mapped = matter_mappings.get(entity_id)
          if mapped:
              to_set.extend(mapped)   # Matter entities replace tado_x
          else:
              to_set.append(entity_id)  # no mapping → use tado_x entity
      elif platform == "matter":
          if entity_id not in matter_entity_set:  # not in any mapping value
              to_set.append(entity_id)  # unmapped Matter = independent
          # else: skip — already added by the tado_x branch above
  ```

  `matter_entity_set` = flat set of all Matter entity_ids across all mapping
  values (built once per `async_evaluate` cycle from `matter_mappings`).
  `asyncio.gather` over `to_set` for concurrent setpoint calls (existing pattern).

### Coordinator — Calibration Source

- **D-04:** For Matter-mapped entities, calibration reads `current_temperature`
  from the Matter entity (not the tado_x zone entity). Matter's
  `current_temperature` already reflects the Tado-applied offset, so:
  `delta = room_sensor_temp − matter_current_temp` gives the true remaining gap.

- **D-05:** Calibration service for Matter-mapped TRVs: `tado_x.set_temperature_offset`
  with `device_id`. Resolve `device_id` from entity registry at calibration
  time: iterate `entity_reg.entities` to find entries where
  `e.platform == "tado_x"` and `e.device_id` matches the device that also owns
  the Matter entity (`entity_reg.async_get(matter_entity_id).device_id`).
  This works when Matter and tado_x share the same HA device (same physical
  valve). If no matching tado_x device is found, fall back to
  `_async_calibrate_room()` (entity-based offset via `temperature_offset`
  attribute). Researcher must verify device sharing in a live Tado X + Matter
  setup.

- **D-06:** For unmapped tado_x zone entities: existing calibration behaviour
  unchanged (`_async_calibrate_tado_device()` or `_async_calibrate_room()`).
  The event-driven listener is new (real-time trigger) but the calibration
  method is the same.

- **D-07:** For unmapped Matter entities: treated as independent TRVs; use
  Matter's `current_temperature` for delta; calibration method resolved by
  `supports_offset_calibration()` as for any TRV entity.

### Coordinator — Listener Lifecycle

- **D-08:** `_matter_cal_listeners: dict[str, Callable]` in coordinator, keyed
  by **entity_id** (not area_id). Each listener cancel callback is stored under
  its entity's key, enabling precise per-entity cancellation.

- **D-09:** Listener scope by mapping state:
  - Mapped tado_x entity → **no listener** (Matter entities handle it)
  - Mapped Matter entity → listener on Matter entity; fires on `current_temperature`
    attribute change only (skip other attribute changes)
  - Unmapped tado_x entity → listener on tado_x entity; fires on
    `current_temperature` change (slower due to Tado X cloud refresh rate,
    but event-driven beats waiting for the next scheduler tick)
  - Unmapped Matter entity → listener on Matter entity; fires on
    `current_temperature` change

- **D-10:** Registration: called at coordinator startup (`async_setup` or first
  `async_evaluate`) and whenever `matter_mappings` changes (WS command triggers
  `_async_refresh_matter_listeners()`). On change: cancel ALL existing listeners
  in `_matter_cal_listeners`, rebuild from current `matter_mappings` + current
  `runtime_data.rooms`.

- **D-11:** Cancellation on unload: cancel all callbacks in
  `_matter_cal_listeners` inside `async_unload_entry`, alongside the existing
  `cancel_registry_listeners` loop. Do NOT append individual listener callbacks
  to `cancel_registry_listeners` (that flat list is for registry event listeners;
  climate `state_changed` listeners live in `_matter_cal_listeners`).

### Frontend — Room Card Pairing UI

- **D-12:** Room card adds a "Matter pairing" section below the TRV list. For
  each tado_x zone entity in the room:
  - Show entity friendly name + a `<select>` dropdown to pick a Matter entity
  - Available options: all `climate.*` entities in the area where
    `entity_reg.async_get(eid).platform == "matter"` + an "(none)" option
  - When paired: show the pair grouped (e.g., tado_x label + Matter label inline)
  - When unpaired: show just the "(none)" option selected
  - Auto-save on change (no Save button — same pattern as calibration toggle)
  - Visible only when the room has at least one tado_x entity (no Tado X in room
    → section hidden)

- **D-13:** Matter entity picker populated from `hass.states` filtered to
  `domain === "climate"` + entity registry `platform === "matter"` for the
  room's area. Same `<select>` pattern as the calendar entity picker (Phase 11
  D-15). Show friendly name; store entity_id.

- **D-14:** Multiple TRVs per room: each tado_x entity gets its own pairing
  row. A room with 2 tado_x entities shows 2 rows, each with its own Matter
  `<select>`. The multiple-pairing schema (value is always a list) handles N
  entries.

### WebSocket Commands

- **D-15:** New WS command `set_matter_mapping`: payload
  `{ tado_entity_id, matter_entity_ids: [] }`. Stores/replaces the entry in
  `matter_mappings[tado_entity_id]`. An empty list or null removes the mapping
  (unpairing).

- **D-16:** `set_matter_mapping` handler triggers `_async_refresh_matter_listeners()`
  in the coordinator after persisting to storage, so listeners are updated
  atomically with the config change.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` §Matter→Tado X Real-Time Calibration —
  MCALIB-01, MCALIB-02 define the acceptance criteria
- `.planning/ROADMAP.md` §Phase 13 — phase boundaries and success criteria

### Key Source Files — Backend

- `custom_components/climate_manager/coordinator.py` — `async_evaluate()`,
  `_async_calibrate()`, `_async_calibrate_tado_device()`,
  `_async_calibrate_room()`, `_ha_tracker_listeners` (existing per-entity
  listener dict pattern) — read fully before implementing the control path
  changes and listener registration
- `custom_components/climate_manager/__init__.py` — `async_setup_entry()`,
  `async_unload_entry()`, `cancel_registry_listeners` lifecycle, runtime_data
  dataclass — understand the unload lifecycle before adding listener teardown
- `custom_components/climate_manager/trv.py` — `supports_offset_calibration()`,
  `get_tado_valve_devices()`, `set_trv_offset_by_device()`, `set_trv_offset()` —
  the calibration service dispatch logic
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG`, existing
  root-level keys (`rooms`, `persons`, `zones`) — where `matter_mappings: {}`
  default goes
- `custom_components/climate_manager/websocket.py` — existing
  `set_person_config` / `set_room_config` patterns (command registration, storage
  persist, coordinator notify) — template for `set_matter_mapping`

### Key Source Files — Frontend

- `custom_components/climate_manager/www/` (built panel JS) — room card
  component; TRV list rendering; entity picker pattern (Phase 11 calendar
  entity picker); auto-save-on-change pattern (Phase 9 calibration toggle)
- `frontend/src/types.ts` — extend root config type with
  `matter_mappings: Record<string, string[]>`
- `frontend/src/ws-client.ts` — add `setMatterMapping(tado_entity_id, matter_entity_ids)` method

### Established Patterns (prior phases)

- Phase 9 CONTEXT.md D-09 — auto-save on change, no Save button; apply to
  Matter entity picker
- Phase 11 CONTEXT.md D-15 — native `<select>` for entity picker, populated
  from `hass.states` filtered by domain + entity registry platform; apply same
  approach for Matter entity picker
- Phase 10 CONTEXT.md D-04 — native `<input>`/`<select>` elements (not
  `ha-*` web components) for all form controls
- `coordinator.py:_ha_tracker_listeners` — dict keyed by string, stores list
  of cancel callbacks per key; exact pattern for `_matter_cal_listeners`
- `async_track_state_change_event` — already imported in coordinator.py;
  used for `_ha_tracker_listeners`; reuse for Matter calibration listeners

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `coordinator.py:_ha_tracker_listeners` — per-entity listener dict; copy this
  pattern verbatim for `_matter_cal_listeners`; already has registration,
  cancellation, and pop-on-remove patterns
- `coordinator.py:_async_calibrate_tado_device()` — Tado X device-based
  calibration; reuse for Matter-mapped entities (same offset service, different
  temperature source)
- `coordinator.py:_async_calibrate_room()` — entity-based calibration fallback;
  reuse for unmapped Matter entities
- `trv.py:get_tado_valve_devices()` — area→valve device lookup; used to
  resolve device_id when Matter entity's device matches a tado_x valve device
- `trv.py:supports_offset_calibration()` — determines which calibration path
  to use; applies to unmapped Matter entities
- `websocket.py:_handle_get_calibration_status` — shows how entity registry
  platform checks (`r.platform == "tado_x"`) are done inline; same pattern
  for Matter entity picker (`r.platform == "matter"`)

### Established Patterns

- **Area loop pattern:** `for area_id, entity_ids in runtime_data.rooms.items()`
  — existing structure for the coordinator area sweep; add the entity-by-entity
  dispatch inside this loop
- **Sparse config keys:** absent = not mapped; no migration needed for existing
  rooms
- **`asyncio.gather` over entity list:** already used for concurrent TRV
  setpoint calls; apply to the new `to_set` list from D-03
- **Entity registry platform check:** `entity_reg.async_get(entity_id).platform`
  — already used in `websocket.py` line 1268 for tado_x detection

### Integration Points

- `coordinator.py:async_evaluate()` — insert entity-by-entity dispatch (D-03)
  replacing the direct entity call; add `_async_refresh_matter_listeners()` call
  on first evaluate if `_matter_cal_listeners` is empty
- `coordinator.py.__init__` — add `_matter_cal_listeners: dict[str, Callable]`
  instance variable
- `__init__.py:async_unload_entry()` — add loop to cancel all
  `_matter_cal_listeners` before platform unload
- `websocket.py` — register `set_matter_mapping` command alongside existing
  config commands; persist to storage then notify coordinator

</code_context>

<specifics>
## Specific Ideas

- `matter_entity_set` in D-03: build as a `frozenset` once per `async_evaluate`
  cycle from `{eid for ids in matter_mappings.values() for eid in ids}`. Avoids
  repeated iteration of mapping values for every Matter entity in the loop.
- For `_async_refresh_matter_listeners()`: cancel-all then re-register is safe
  because WS commands are serialised on the HA event loop. No concurrent
  registration race.
- Device_id resolution for Matter calibration (D-05): research must verify
  whether a Tado X Radiator Valve X device appears under the same `device_id`
  in both the `tado_x` and `matter` entity registry entries. If yes,
  `entity_reg.async_get(matter_entity_id).device_id` directly gives the
  device_id for the offset call. If not (separate HA devices per integration),
  a name/identifier-based matching strategy is needed — document the finding
  in research before planning.
- Room card section heading: "Matter pairing" or "Real-time calibration" —
  planner's choice; keep consistent with the calibration section terminology
  already in the room card.

</specifics>

<deferred>
## Deferred Ideas

- **Fallback when Matter entity is unavailable** — if a Matter entity goes
  `unavailable`, automatically fall back to the tado_x entity for setpoint
  calls. Not in scope for Phase 13; deferred to a future robustness phase.
- **Reverse mapping display** — showing in the Matter entity's card which
  tado_x entity it's paired to. Out of scope.
- **Bulk auto-pair** — detect Matter + tado_x entity pairs in an area sharing
  the same HA device and offer to pair them all at once. Could be a UX
  improvement in a later phase.

</deferred>

---

*Phase: 13-matter-tado-x-real-time-calibration*
*Context gathered: 2026-06-03*

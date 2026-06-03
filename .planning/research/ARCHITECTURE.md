# Architecture Patterns

**Project:** Climate Manager v1.3 — Calendar Presence & Pre-heat
**Researched:** 2026-05-31

## Existing Architecture (v1.2 baseline)

```
async_setup_entry
  ├── ClimateManagerStore (storage.py) — Store-backed persistence
  ├── discover_rooms / discover_persons / discover_room_sensors
  ├── ClimateManagerData (runtime_data dataclass on ConfigEntry)
  │     ├── runtime_config: dict (merged DEFAULT_CONFIG + stored data)
  │     ├── rooms: {area_id → [entity_ids]}
  │     ├── persons: [person.* entity_ids]
  │     ├── room_auto_sensors: {area_id → {temperature, humidity}}
  │     ├── coordinator: ClimateManagerCoordinator
  │     ├── cancel_scheduler: Callable
  │     └── cancel_registry_listeners: list[Callable]
  ├── ClimateManagerCoordinator.async_evaluate() — minute-poll loop
  │     ├── _compute_present_persons()
  │     ├── _compute_desired_temps()       # PASS 1: zone/schedule baseline
  │     ├── _apply_presence_overrides()    # PASS 2: presence mutations
  │     ├── _push_temperatures()           # asyncio.gather over all TRVs
  │     ├── hass.bus.async_fire(status_update)
  │     └── _async_calibrate()             # Tado X offset correction
  ├── websocket.async_register_commands() — 20 WS command factories
  ├── hass.http.async_register_static_paths(www/)
  └── panel_custom.async_register_panel()

schedule.py  — pure Python, no HA imports
  ├── evaluate_schedule(program, now)
  ├── resolve_presence(person_config, now)
  ├── compute_occupied_temp(program, now, is_present, temps)
  └── validate_daily_program(program)

trv.py — HA-aware helpers
  ├── is_trv_entity / supports_hvac_off / supports_offset_calibration
  ├── set_trv_temperature (two-call: set_hvac_mode heat → set_temperature)
  ├── set_trv_off / set_trv_offset / set_trv_offset_by_device
  └── get_tado_valve_devices (device registry scan for Radiator Valve X)

Frontend (Lit/TypeScript, single panel.js)
  ├── global-settings-tab.ts
  ├── rooms-tab.ts
  ├── persons-tab.ts
  ├── zone-tab.ts
  └── ws-client.ts (home-assistant-js-websocket)
```

## Component Boundaries for v1.3 Features

### Feature 1: Pronote Presence Source

**New vs Modified:**

- **NEW** `presence/__init__.py` — package marker
- **NEW** `presence/pronote.py` — `async_fetch_pronote_timetable(config)`
  returns normalized `{date: [{"start": "HH:MM", "state": "absent|present"}]}`
  slots. Contains all credential handling and network I/O. Uses aiohttp
  (already available in HA environment — no new PyPI dep needed) or
  `hass.async_add_executor_job` wrapping a sync call.
- **MODIFIED** `const.py` — add `PRESENCE_PRONOTE = "pronote"` constant;
  add pronote cache key to DEFAULT_CONFIG persons sub-schema comment
- **MODIFIED** `schedule.py` — `resolve_presence()` gains a `pronote` mode
  branch that reads cached timetable from person_config; pure Python, no
  network. Falls back to `scheduled` behaviour on missing cache key.
- **MODIFIED** `coordinator.py` — new `_async_refresh_presence_sources()`
  async method called at the top of `async_evaluate()`. Iterates persons
  with `mode == "pronote"`, checks cache TTL (1 hour), calls
  `async_fetch_pronote_timetable`, writes result into
  `runtime_config["persons"][person_id]["pronote_cache"]`, persists via
  `store.async_save`.
- **MODIFIED** `websocket.py` — extend `set_person_config` schema to accept
  `pronote_url`, `pronote_username`, `pronote_password` fields stored
  in runtime_config.
- **MODIFIED** `types.ts` — extend `PersonConfig` with optional
  `pronote_url?: string`, `pronote_username?: string`,
  `pronote_password?: string`
- **MODIFIED** `persons-tab.ts` — add Pronote credential input fields
  when mode == "pronote"

**Data flow:**
```
async_evaluate()
  └── _async_refresh_presence_sources()
        └── async_fetch_pronote_timetable() → runtime_config.persons[id].pronote_cache
              ↓ (same tick, after cache written)
  └── _compute_present_persons()
        └── resolve_presence() reads pronote_cache to determine present/absent
```

**Integration point:** `resolve_presence()` in `schedule.py` is the single
entry point for all presence determination. Adding `pronote` as a new mode
constant is a clean additive extension — no existing branches are touched.

**Fallback:** If `pronote_cache` is absent or stale and fetch fails,
`resolve_presence()` falls back to `scheduled` mode (uses existing `schedule`
field). Cache refresh failures log as WARNING, not ERROR.

---

### Feature 2: iCal Presence Source

**New vs Modified:**

- **NEW** `presence/ical.py` — `async_fetch_ical(url)` parses ICS content.
  No credentials — URL only (supports private Google Calendar `.ics` export
  URLs). Returns same normalized slot format as Pronote. Uses aiohttp for
  the HTTP fetch; `icalendar` PyPI lib for parsing (or minimal stdlib parser
  to avoid dependency).
- **MODIFIED** `const.py` — add `PRESENCE_ICAL = "ical"` constant
- **MODIFIED** `schedule.py` — `resolve_presence()` gains `ical` mode branch,
  mirrors Pronote branch but reads `ical_cache`
- **MODIFIED** `coordinator.py` — `_async_refresh_presence_sources()` also
  handles `mode == "ical"` persons; calls `async_fetch_ical(url)`
- **MODIFIED** `websocket.py` — `set_person_config` schema accepts `ical_url`
- **MODIFIED** `types.ts` — extend `PersonConfig` with `ical_url?: string`
- **MODIFIED** `persons-tab.ts` — add iCal URL input field when mode == "ical"

**Integration point:** Identical to Pronote. Both sources share the same
`_async_refresh_presence_sources()` loop; only the fetch function and config
keys differ.

**Shared cache model in persons[person_id]:**
```python
{
  "mode": "pronote" | "ical",
  "pronote_url": "...",              # Pronote only
  "pronote_username": "...",
  "pronote_password": "...",
  "ical_url": "...",                 # iCal only
  "pronote_cache": {                 # keyed by ISO date string
    "2026-06-02": [{"start": "08:00", "state": "absent"}, ...]
  },
  "ical_cache": {
    "2026-06-02": [...]
  },
  "presence_cache_fetched_at": "2026-06-02T07:00:00+02:00"  # shared TTL ts
}
```

---

### Feature 3: Predictive Pre-heat

**New vs Modified:**

- **NEW** `preheat.py` — pure Python module, no HA imports:
  - `get_next_period_start(daily_program, now) → datetime | None`
  - `compute_lead_time(inertia_factor, delta_temp) → timedelta`
  - `should_preheat(room_config, daily_program, now, period_temps) → bool`
  Returns True when the next period transition is within lead time and the
  next period is warmer than the current one.
- **MODIFIED** `coordinator.py` — new PASS 0 before `_compute_desired_temps()`:
  `_apply_preheat_overrides(config, rooms, desired_temps, room_periods, now)`.
  For rooms with `preheat_enabled=True`, calls `should_preheat()` and, if
  True, sets `desired_temps[area_id]` to the next period's temperature early.
  Records `"pre_heating"` in `room_periods[area_id]` for status display.
  New coordinator instance field: `_preheat_inertia_samples: dict[str, list[float]]`
  for rolling inertia learning (cap at N=10 per room).
- **MODIFIED** `const.py` — add `PERIOD_PRE_HEATING = "pre_heating"` constant;
  add preheat sub-schema to rooms section comment
- **MODIFIED** `websocket.py` — extend `set_room_config` schema to accept
  `preheat_enabled: bool`, `preheat_max_duration: int` (minutes),
  `inertia_factor: float` (minutes/°C). The `_build_status_payload()`
  already passes `room_periods` through — no change needed there.
- **MODIFIED** `types.ts` — extend `RoomConfig` with `preheat_enabled?: bool`,
  `preheat_max_duration?: number`, `inertia_factor?: number`
- **MODIFIED** `rooms-tab.ts` — add pre-heat toggle and config inputs in room
  settings; display "Pre-heating" badge when active_period == "pre_heating"

**Storage additions** (additive to existing rooms sub-schema):
```python
# rooms[area_id] new optional keys
{
  "preheat_enabled": True,
  "preheat_max_duration": 60,   # cap: never pre-heat more than N minutes early
  "inertia_factor": 4.5,        # minutes per °C (learned or manually set)
  "inertia_samples": [4.2, 4.8] # rolling window, max 10 entries
}
```

**Pre-heat algorithm:**
```
next_start = get_next_period_start(program, now)
next_temp = period_temps[mode_at(next_start)]
current_temp = period_temps[current_period]
delta = next_temp - current_temp
if delta <= 0: return False   # cooling or same — no pre-heat
lead_time = min(inertia_factor * delta, preheat_max_duration)
return (next_start - now) <= timedelta(minutes=lead_time)
```

**Integration point:** PASS 0 runs before PASS 1 (`_compute_desired_temps`).
Results are written into `desired_temps` and `room_periods` using the same
dict mutations as PASS 1/2, so `_push_temperatures()` is unchanged. The
coordinator's `_build_status_payload()` picks up `"pre_heating"` period from
`room_periods` automatically via the existing room_periods passthrough.

---

### Feature 4: Matter→Tado X Sensor Mapping

**New vs Modified:**

- **MODIFIED** `coordinator.py` — new `_setup_matter_listeners()` method.
  Iterates rooms, reads `rooms[area_id].matter_sensor_map`
  (`{matter_entity_id: tado_device_id}`), registers
  `async_track_state_change_event` for each Matter entity. On state_changed:
  immediately calls `_async_calibrate_tado_device()` for that room, bypassing
  the 1-minute poll. Returns list of cancel callables stored on runtime_data.
- **MODIFIED** `__init__.py` — `ClimateManagerData` gains
  `cancel_matter_listeners: list[Callable]` field (same pattern as
  `cancel_registry_listeners`); `async_unload_entry` cancels them;
  `async_setup_entry` calls `_setup_matter_listeners()` after coordinator init.
- **MODIFIED** `const.py` — add `matter_sensor_map` to rooms sub-schema
  comment
- **MODIFIED** `websocket.py` — extend `set_room_config` to accept
  `matter_sensor_map: dict[str, str]` (Matter entity_id → Tado device_id).
  After `store.async_save` succeeds, trigger `_setup_matter_listeners()` to
  cancel old and register new listeners.
- **MODIFIED** `trv.py` — optional: add
  `get_tado_device_id_for_name(hass, name) → str | None` helper for UI
  name-to-device_id resolution in the mapping picker.
- **MODIFIED** `types.ts` — extend `RoomConfig` with
  `matter_sensor_map?: Record<string, string>`
- **MODIFIED** `rooms-tab.ts` — add Matter→Tado mapping picker UI per room
  (select Matter sensor entity + Tado device name dropdown)

**Data flow:**
```
HA state_changed event (Matter temperature entity)
  └── _handle_matter_state_change(area_id, matter_entity_id, event)
        └── guard: calibration_enabled? delta > threshold?
              └── _async_calibrate_tado_device(area_id, device_id, ...)
                    └── set_trv_offset_by_device()   [immediate, sub-minute]
```

**Listener lifecycle:** Cancel callbacks stored in
`ClimateManagerData.cancel_matter_listeners`. Cancelled in
`async_unload_entry`. Re-registered when `set_room_config` mutates
`matter_sensor_map` (cancel all → rebuild). Template: existing
`cancel_registry_listeners` pattern in `__init__.py`.

**Guard required in listener:** Must check `config.get("calibration_enabled")`
and apply delta threshold before issuing any offset call — mirrors the
existing guard in `_async_calibrate_tado_device()`.

---

### Feature 5: Hide HA Presence Mode (Frontend Only)

**New vs Modified:**

- **MODIFIED** `persons-tab.ts` — in the mode selector, filter out the "ha"
  option when `hass.states[personId]?.attributes?.device_trackers?.length === 0`
  or the attribute is absent. `hass.states` is already available via
  `this.hass` in the Lit panel. No backend changes needed.

**Integration point:** Pure frontend read of `hass.states`. The `hass` object
is passed into the Lit panel element on every HA state update. Zero WebSocket
commands, zero Python changes.

---

## Component Dependency Map

```
Feature 1 (Pronote)
  presence/pronote.py ← coordinator.py ← schedule.py ← const.py
  websocket.py (set_person_config extended) ← persons-tab.ts

Feature 2 (iCal)
  presence/ical.py ← coordinator.py ← schedule.py ← const.py
  websocket.py (set_person_config extended) ← persons-tab.ts

Feature 3 (Pre-heat)
  preheat.py ← coordinator.py ← const.py
  websocket.py (set_room_config extended) ← rooms-tab.ts

Feature 4 (Matter→Tado)
  trv.py ← coordinator.py ← __init__.py
  websocket.py (set_room_config extended) ← rooms-tab.ts

Feature 5 (Hide HA mode)
  persons-tab.ts only — no backend
```

## Files Modified vs Created Summary

| File | Status | Features |
|------|--------|----------|
| `presence/__init__.py` | NEW (package) | 1, 2 |
| `presence/pronote.py` | NEW | 1 |
| `presence/ical.py` | NEW | 2 |
| `preheat.py` | NEW | 3 |
| `const.py` | MODIFIED | 1, 2, 3, 4 |
| `schedule.py` | MODIFIED | 1, 2 |
| `coordinator.py` | MODIFIED | 1, 2, 3, 4 |
| `trv.py` | MODIFIED | 4 |
| `__init__.py` | MODIFIED | 4 |
| `websocket.py` | MODIFIED | 1, 2, 3, 4 |
| `types.ts` | MODIFIED | 1, 2, 3, 4 |
| `persons-tab.ts` | MODIFIED | 1, 2, 5 |
| `rooms-tab.ts` | MODIFIED | 3, 4 |

## Suggested Build Order

### Phase 1 — Feature 5 (quick task, standalone)

Build "hide HA mode" first. Zero backend, zero risk. Ships immediately as a
standalone quick task before any other phase work begins.

### Phase 2 — Features 1 and 2 (calendar presence sources together)

Build Pronote and iCal together as one phase — they touch identical files,
share the `_async_refresh_presence_sources()` loop, and use the same cache
model. Building together avoids touching coordinator.py / schedule.py twice:

1. Add `PRESENCE_PRONOTE` and `PRESENCE_ICAL` to `const.py`
2. Create `presence/` package with `pronote.py` and `ical.py` fetch functions
3. Extend `resolve_presence()` in `schedule.py` with two new mode branches
   (pure Python — unit test in isolation first)
4. Add `_async_refresh_presence_sources()` to coordinator
5. Extend `set_person_config` WS schema for both source types
6. Extend `PersonConfig` TypeScript types
7. Add credential/URL input UI in `persons-tab.ts` for both modes

**Dependency:** No dependency on Features 3 or 4.

### Phase 3 — Feature 3 (predictive pre-heat)

1. Build `preheat.py` as a pure Python module (unit-testable in isolation)
2. Add PASS 0 (`_apply_preheat_overrides`) injection into coordinator —
   this is the highest-risk change; test thoroughly before moving on
3. Add preheat config keys to rooms storage schema and `const.py` comment
4. Extend `set_room_config` WS schema
5. Extend `RoomConfig` TypeScript type
6. Add pre-heat toggle and config UI in `rooms-tab.ts`

**Dependency:** None on Phase 2. Build `preheat.py` pure-Python first; only
integrate into coordinator once pure-module tests pass.

**Deferral candidate:** Adaptive inertia learning (`inertia_samples` rolling
update) can ship as a follow-up quick task. Phase 3 ships with manual
`inertia_factor` and a sensible default (4 min/°C).

### Phase 4 — Feature 4 (Matter→Tado real-time calibration)

1. Add `cancel_matter_listeners` to `ClimateManagerData` in `__init__.py`
2. Implement `_setup_matter_listeners()` in coordinator
3. Wire into `async_setup_entry` and `async_unload_entry`
4. Add re-registration trigger in `set_room_config` WS handler
5. Extend `set_room_config` WS schema for `matter_sensor_map`
6. Add mapping picker UI in `rooms-tab.ts`

**Dependency:** Requires stable `_async_calibrate_tado_device()` (v1.2,
production-verified). The listener pattern is a direct copy of the existing
`cancel_registry_listeners` mechanism — use it as the implementation template.

**Rationale for last:** Most HA-lifecycle-sensitive feature (new event
listeners, new unload path, re-registration logic). Building after pre-heat
minimises blast radius in coordinator.py.

## Cross-Cutting Patterns to Preserve

**Write-then-Evaluate** (all WS write handlers):
`mutate → store.async_save → send_result → hass.async_create_task(async_evaluate())`
Exception: config-only changes that don't affect current-tick temperatures
(e.g. updating credentials, matter_sensor_map) need not trigger async_evaluate.

**Sparse Merge** (all config sub-keys):
`runtime_config.setdefault("persons", {}).setdefault(person_id, {}).update(incoming)`
Never replace the entire persons or rooms dict.

**CR-01 Snapshot Rollback** (all writes that can raise):
Deepcopy the affected sub-dict before mutation; restore on exception.

**Guard Chain** (all async HA calls):
State guard → availability guard → threshold guard → call → WARNING on
exception. Presence fetch failures must never crash `async_evaluate()`.

**Pure-Python Separation**: `schedule.py` and `preheat.py` must have zero HA
imports. All datetime arithmetic and logic belongs there; the coordinator
supplies the prepared arguments.

## Key Architecture Risks

| Risk | Location | Mitigation |
|------|----------|------------|
| Pronote/iCal HTTP I/O blocking the event loop | coordinator.py | Use aiohttp (async) or hass.async_add_executor_job for any sync HTTP lib |
| Matter listener leak on set_room_config mutation | coordinator.py | Cancel all existing matter listeners before re-registering after save |
| Pre-heat PASS 0 overriding PASS 2 presence result | coordinator.py | Run PASS 0 before PASS 1; PASS 2 presence still overwrites — correct (presence wins over pre-heat baseline) |
| pronote_cache / ical_cache stored in plaintext in Store | store.py | Acceptable for local HA; note in code; formal secrets handling is out of scope |
| Cache TTL fetch blocking minute tick | coordinator.py | Fire fetch as `hass.async_create_task` on cache miss; use cached value (possibly stale) this tick — never await on slow network in the hot path |
| inertia_samples growing unbounded in Store | preheat.py | Enforce N=10 rolling window cap inside preheat.py before writing back |

## Sources

- Codebase analysis: coordinator.py, schedule.py, trv.py, websocket.py,
  __init__.py, const.py, types.ts (all read directly from v1.2 production code)
- HA async_track_state_change_event pattern: existing cancel_registry_listeners
  mechanism in __init__.py used as implementation template for Feature 4
- Pure-Python module pattern: schedule.py as template for preheat.py

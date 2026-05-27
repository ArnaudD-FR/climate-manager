# Phase 5: Zone CRUD & Evaluation Engine - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Add WebSocket commands for zone CRUD operations and refactor the coordinator to evaluate each zone independently. No frontend UI — that's Phase 6.

**In scope:**
- 6 new WS commands: create_zone, delete_zone, rename_zone, set_zone_mode, set_zone_time_program, reset_zone_time_program
- Coordinator refactored to resolve each room's zone and evaluate by zone mode (not global_mode as a system-wide switch)
- Room custom schedule (room_mode=custom) still overrides zone evaluation (EVAL-05 — existing logic preserved)

**Out of scope:**
- Frontend UI (Phase 6)
- Zone assignment UI/UX (Phase 6)
- Per-zone temperature setpoints (v2)

</domain>

<decisions>
## Implementation Decisions

### Initial Zone State (create_zone)
- **D-01:** New zone mode defaults to `time_program` — matches `DEFAULT_GLOBAL_MODE` in const.py. Zone is active and follows a schedule from creation.
- **D-02:** New zone time_program is a `copy.deepcopy(global_time_program)` at creation time. The user has already tuned the global schedule; a new zone is likely a variant of it.
- **D-03:** `create_zone` returns the full zone config object `{zone_id, name, mode, time_program}` so Phase 6 frontend can render the new zone tab immediately without a second `get_config` call.

### WebSocket Command Set
- **D-04:** Zone CRUD uses separate commands per concern — mirrors the existing granular pattern (set_global_mode / set_time_program / set_room_config are separate):
  - `climate_manager/create_zone` — `{name: str}` → returns `{zone_id, name, mode, time_program}`
  - `climate_manager/delete_zone` — `{zone_id: str}` → moves all zone rooms to Default Zone, removes zone entry
  - `climate_manager/rename_zone` — `{zone_id: str, name: str}` → updates zone name (works for Default Zone via zone_id="default" sentinel or renaming default_zone_name directly)
  - `climate_manager/set_zone_mode` — `{zone_id: str, mode: vol.In(VALID_MODES)}` → updates zone.mode
  - `climate_manager/set_zone_time_program` — `{zone_id: str, program: dict}` → validates via validate_daily_program then persists
  - `climate_manager/reset_zone_time_program` — `{zone_id: str, target: vol.In(['default', 'global'])}` → 'default' resets to `copy.deepcopy(_DEFAULT_DAILY_PROGRAM)`, 'global' copies from `global_time_program`
- **D-05:** rename_zone must support renaming the Default Zone (which stores its name in `default_zone_name`, not in `zones{}`). The handler checks `zone_id == "default"` (or a sentinel) and routes accordingly.
- **D-06:** All zone write commands follow the write-then-evaluate pattern: mutate runtime_config → store.async_save → send_result → coordinator.async_evaluate (background). Same as existing write handlers.

### Evaluation Architecture (CRITICAL — breaks from v1.0 model)
- **D-07:** **Zones are fully independent.** `global_mode` is the Default Zone's mode — not a system-wide override. Custom zone rooms are never governed by `global_mode`.
- **D-08:** When `global_mode=off` (Default Zone is off), rooms in custom zones are **unaffected** — they follow their own zone's mode. The coordinator's current top-level branch on `global_mode` (which applies to ALL rooms) must be replaced.
- **D-09:** The new evaluation algorithm per room:
  1. Determine the room's zone: `zone_id` absent → Default Zone, else custom zone
  2. For Default Zone rooms: evaluate using `global_mode` + `global_time_program` (same existing logic as v1.0)
  3. For custom zone rooms:
     - zone.mode=off → frost-protection temperature
     - zone.mode=time_program → `zone.time_program`
     - zone.mode=time_program_presences → `zone.time_program` + all-persons presence override
  4. Room custom schedule (room_mode=custom) always overrides zone evaluation at step 3 (EVAL-05)
- **D-10:** EVAL-04 is NOT a cross-zone override. "Global mode=time_program_presences governs presence for all rooms" means Default Zone rooms with presences mode get presence logic — it does not propagate to custom zones.

### Zone Presence Semantics (EVAL-03)
- **D-11:** When a custom zone has mode=time_program_presences, **all configured persons** are considered — not scoped to persons whose room_ids overlap with the zone. Same person list as the Default Zone presence evaluation.
- **D-12:** The zone's own `time_program` is the base schedule for presence computation (compute_occupied_temp uses zone.time_program). Room custom schedule (room_mode=custom) still wins over zone.time_program (EVAL-05).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### WebSocket API Patterns
- `custom_components/climate_manager/websocket.py` — All 11 existing WS handlers. Use as the template for zone command factories: vol schema validation, write-then-evaluate pattern, CR-01 snapshot-rollback for validation failures, `@websocket_api.async_response` + `@callback` decoration patterns.

### Evaluation Engine
- `custom_components/climate_manager/coordinator.py` — Current evaluation engine. `_evaluate_time_program` and `_evaluate_time_program_presences` iterate ALL rooms using global_mode. Both methods must be refactored to route rooms through zone resolution first (D-07/D-08/D-09). `_compute_present_persons` and `compute_occupied_temp` logic are reusable for zone presence evaluation.
- `custom_components/climate_manager/schedule.py` — `evaluate_schedule`, `compute_occupied_temp`, `resolve_presence` are all reusable as-is for zone evaluation. No changes expected here.

### Storage Schema
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG` (zones schema), `_DEFAULT_DAILY_PROGRAM` (used by reset_zone_time_program target='default'), `VALID_MODES`, `PERIOD_FROST_PROTECTION`. Zone object shape defined in the comment block at lines 152–170.
- `custom_components/climate_manager/storage.py` — `validate_zone_assignment` is called inside `async_save`. `delete_zone` handler must null out `zone_id` on moved rooms before saving.

### Requirements
- `.planning/REQUIREMENTS.md` — ZONE-05..09 (zone CRUD) and EVAL-01..05 (evaluation hierarchy). Read carefully — EVAL-04 is clarified in D-10 above.
- `.planning/ROADMAP.md` — Phase 5 success criteria: 5 behavioural scenarios to verify.

### Prior Phase Context
- `.planning/phases/04-zone-data-model-storage/04-CONTEXT.md` — D-01..07 from Phase 4 are foundational. Especially D-01 (Default Zone is virtual), D-06 (absent zone_id = Default Zone), D-07 (UUID zone keys).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `websocket.py` factory pattern `_make_ws_*(entry)` — all zone command handlers use the same factory closure. Reuse verbatim.
- `schedule.py` — `evaluate_schedule(daily_program, now)`, `compute_occupied_temp(daily_program, now, is_present, period_temperatures)`, `resolve_presence(person_config, now)` are all reusable for zone-level evaluation without modification.
- `coordinator._compute_present_persons(config, now)` — reusable for presence resolution in zone=time_program_presences evaluation.

### Established Patterns
- **Write-then-evaluate:** All write handlers do: mutate runtime_config → store.async_save → send_result → `hass.async_create_task(coordinator.async_evaluate())`. Zone write commands follow this exactly.
- **CR-01 snapshot-rollback:** `set_room_config` takes a deepcopy snapshot before mutation; rolls back if `async_save` raises `ValueError`. Same pattern needed for `delete_zone` (moves rooms) and any zone command where `validate_zone_assignment` might reject.
- **vol schema validation:** `vol.In(VALID_MODES)` for mode fields, `vol.Coerce(str)` for IDs. Zone commands validate mode via `vol.In(VALID_MODES)` in the schema, not in the handler body.
- **validate_daily_program gate:** `set_time_program` sends error and returns BEFORE save if program invalid (T-03-05). `set_zone_time_program` must do the same.
- **Sparse storage:** Only non-default values written. Zone entries only appear in `zones{}` if they exist. Default Zone has no storage entry.

### Integration Points
- `async_register_commands` in `websocket.py:68` — 6 new `websocket_api.async_register_command` calls added here for zone commands.
- `coordinator.async_evaluate` — the per-room evaluation loop must be restructured to route rooms through zone resolution (D-09). The `_evaluate_time_program` and `_evaluate_time_program_presences` methods will likely be replaced or wrapped by a zone-aware dispatch.
- `entry.runtime_data.rooms` — the `{area_id: [entity_id,...]}` dict used in coordinator. Room zone resolution reads `runtime_config["rooms"].get(area_id, {}).get("zone_id")`.
- `runtime_config["zones"]` — the zone store accessed by all zone handlers and the coordinator's zone resolution step.

</code_context>

<specifics>
## Specific Ideas

- `create_zone` UUID generation: `str(uuid.uuid4())` in the handler body (import uuid at top of websocket.py).
- `rename_zone` Default Zone routing: check `zone_id == "default"` (use a sentinel string) → update `runtime_config["default_zone_name"]`; else update `runtime_config["zones"][zone_id]["name"]`.
- `delete_zone` room migration: iterate `runtime_config["rooms"]`, for each room where `room.get("zone_id") == zone_id`, pop the `zone_id` key (sparse model — absent = Default Zone). Then `del runtime_config["zones"][zone_id]`. Save once after both mutations.
- `reset_zone_time_program(zone_id, target='default')` → `runtime_config["zones"][zone_id]["time_program"] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM)`
- `reset_zone_time_program(zone_id, target='global')` → `runtime_config["zones"][zone_id]["time_program"] = copy.deepcopy(runtime_config["global_time_program"])`
- Coordinator zone resolution helper (suggested to planner): a `_resolve_zone_config(area_id) → (mode, time_program)` method or inline lookup per room avoids duplication across `_evaluate_time_program` / `_evaluate_time_program_presences`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-Zone CRUD & Evaluation Engine*
*Context gathered: 2026-05-27*

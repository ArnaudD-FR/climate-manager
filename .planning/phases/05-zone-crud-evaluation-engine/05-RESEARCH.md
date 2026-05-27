# Phase 5: Zone CRUD & Evaluation Engine — Research

**Researched:** 2026-05-27
**Domain:** Home Assistant WebSocket API extension + coordinator evaluation refactor
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Initial Zone State (create_zone)**
- D-01: New zone mode defaults to `time_program` — matches `DEFAULT_GLOBAL_MODE` in const.py.
- D-02: New zone time_program is a `copy.deepcopy(global_time_program)` at creation time.
- D-03: `create_zone` returns the full zone config object `{zone_id, name, mode, time_program}`.

**WebSocket Command Set**
- D-04: Six separate commands (granular pattern):
  - `climate_manager/create_zone` — `{name: str}` → returns `{zone_id, name, mode, time_program}`
  - `climate_manager/delete_zone` — `{zone_id: str}` → moves all zone rooms to Default Zone, removes zone entry
  - `climate_manager/rename_zone` — `{zone_id: str, name: str}` → updates zone name (Default Zone via sentinel "default")
  - `climate_manager/set_zone_mode` — `{zone_id: str, mode: vol.In(VALID_MODES)}` → updates zone.mode
  - `climate_manager/set_zone_time_program` — `{zone_id: str, program: dict}` → validates via validate_daily_program then persists
  - `climate_manager/reset_zone_time_program` — `{zone_id: str, target: vol.In(['default', 'global'])}` → resets zone time_program
- D-05: rename_zone checks `zone_id == "default"` → updates `runtime_config["default_zone_name"]`; else updates `runtime_config["zones"][zone_id]["name"]`.
- D-06: All zone write commands follow the write-then-evaluate pattern.

**Evaluation Architecture (CRITICAL)**
- D-07: Zones are fully independent. `global_mode` is the Default Zone's mode only.
- D-08: `global_mode=off` only affects Default Zone rooms. Custom zone rooms are unaffected.
- D-09: New evaluation algorithm per room — zone resolution first, then mode dispatch:
  1. Determine room's zone: `zone_id` absent → Default Zone, else custom zone
  2. Default Zone rooms: evaluate using `global_mode` + `global_time_program` (existing v1.0 logic)
  3. Custom zone rooms: zone.mode=off → frost-protection; zone.mode=time_program → zone.time_program; zone.mode=time_program_presences → zone.time_program + all-persons presence override
  4. Room custom schedule (room_mode=custom) always overrides zone evaluation (EVAL-05)
- D-10: EVAL-04 is NOT a cross-zone override. Presence with global mode=time_program_presences applies only to Default Zone rooms.

**Zone Presence Semantics (EVAL-03)**
- D-11: When a custom zone has mode=time_program_presences, all configured persons are considered (not scoped to zone rooms).
- D-12: The zone's own `time_program` is the base schedule for presence computation.

### Claude's Discretion

None recorded — all decisions locked.

### Deferred Ideas (OUT OF SCOPE)

None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ZONE-05 | User can create a new custom zone with a name | create_zone WS handler; UUID generation; deepcopy of global_time_program |
| ZONE-06 | User can rename any zone including Default Zone | rename_zone handler; "default" sentinel routing to default_zone_name field |
| ZONE-07 | User can delete a custom zone; rooms move to Default Zone automatically | delete_zone handler; room migration by popping zone_id; snapshot-rollback |
| ZONE-08 | User can set any zone's mode | set_zone_mode handler; vol.In(VALID_MODES) schema gate |
| ZONE-09 | User can edit any zone's weekly time program | set_zone_time_program handler; validate_daily_program gate |
| EVAL-01 | Zone mode=off → all rooms in zone receive frost-protection temperature | Coordinator zone dispatch: off branch pushes PERIOD_FROST_PROTECTION |
| EVAL-02 | Zone mode=time_program → rooms run zone's weekly schedule | Coordinator zone dispatch: time_program branch uses zone.time_program |
| EVAL-03 | Zone mode=time_program_presences → rooms run zone schedule with presence override | Coordinator zone dispatch: _compute_present_persons reused; zone.time_program as base |
| EVAL-04 | Global mode=time_program_presences → presence heating applies to all rooms regardless of zone mode | Clarified by D-10: applies to Default Zone rooms only (D-07 supersedes REQUIREMENTS.md wording) |
| EVAL-05 | Per-room custom schedule overrides zone schedule | room_mode=custom short-circuit before zone resolution; existing ROOM_MODE_CUSTOM logic reused |
</phase_requirements>

---

## Summary

Phase 5 adds 6 WebSocket commands and refactors the coordinator's evaluation loop. The WebSocket layer is a mechanical extension of the existing factory pattern — 11 handlers already exist in websocket.py and every structural decision (factory closure, vol schema validation, write-then-evaluate, CR-01 snapshot-rollback) is established and must be reused verbatim. No new patterns are needed.

The coordinator refactor is the phase's architectural pivot. The current `async_evaluate` branches at the top level on `global_mode`, applying the same logic to all rooms. This must be replaced by per-room zone resolution: each room gets routed to either the Default Zone evaluation path (identical to existing v1.0 logic) or a custom zone evaluation path (new). The existing `_evaluate_time_program` and `_evaluate_time_program_presences` methods contain the right logic for Default Zone rooms but must be restructured so that custom zone rooms execute an equivalent per-zone variant of the same logic.

The key insight for planning: the coordinator refactor is NOT a rewrite. The existing algorithms (`evaluate_schedule`, `compute_occupied_temp`, `resolve_presence`, `_compute_present_persons`) are all correct and reusable. What changes is how rooms are dispatched — zone resolution wraps the existing per-room logic rather than replacing it. The scope is a single method restructure in `async_evaluate` (or its helpers) plus the addition of a zone-aware dispatch path.

**Primary recommendation:** Factor a `_resolve_zone_for_room(area_id) → (mode, time_program)` helper. The existing `_evaluate_time_program` and `_evaluate_time_program_presences` methods then become thin wrappers that call this helper per room instead of reading `global_mode`/`global_time_program` directly.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Zone CRUD (create/rename/delete/set mode/set program) | Backend (WebSocket handlers) | Storage | Handlers mutate runtime_config in-memory, persist via Store; no frontend UI in this phase |
| Zone evaluation dispatch | Backend (Coordinator) | — | `async_evaluate` owns all TRV push decisions; zone resolution is pure coordinator logic |
| Zone ID generation | Backend (WebSocket handler) | — | UUID generated at creation time in `create_zone` handler body; no client input |
| Room-to-zone resolution | Backend (Coordinator) | — | `runtime_config["rooms"][area_id].get("zone_id")` — absent = Default Zone (D-06) |
| Presence override (zone=time_program_presences) | Backend (Coordinator) | — | Same `_compute_present_persons` + `compute_occupied_temp` as global presence; zone.time_program as base |
| Validation (zone_id referential integrity) | Storage (`validate_zone_assignment`) | — | Called inside `async_save`; already enforces ZONE-04 invariants |

---

## Standard Stack

No new external packages. All required tools are already in the integration.

### Core (already present — no installation needed)

| Module | Source | Purpose in Phase 5 |
|--------|--------|---------------------|
| `uuid` (stdlib) | Python stdlib | UUID generation for zone IDs in `create_zone` |
| `copy` (stdlib) | Python stdlib | `copy.deepcopy` for zone time_program initialization and CR-01 snapshots |
| `homeassistant.components.websocket_api` | HA core | WebSocket handler registration and response helpers |
| `voluptuous` | HA dependency | Schema validation in handler decorators |
| `.schedule.validate_daily_program` | project | Program validation gate in `set_zone_time_program` |
| `.schedule.evaluate_schedule` | project | Zone time_program evaluation in coordinator |
| `.schedule.compute_occupied_temp` | project | Zone presence computation in coordinator |
| `.schedule.resolve_presence` | project | Person presence resolution (reused as-is) |
| `.coordinator._compute_present_persons` | project | Person presence list (reused as-is for zone=time_program_presences) |
| `.const._DEFAULT_DAILY_PROGRAM` | project | Used by `reset_zone_time_program(target='default')` |
| `.const.VALID_MODES` | project | `vol.In(VALID_MODES)` schema gate for zone mode fields |
| `.const.PERIOD_FROST_PROTECTION` | project | Zone=off pushes this period's temperature |
| `.storage.validate_zone_assignment` | project | Called inside `async_save`; no direct handler call needed |

## Package Legitimacy Audit

Not applicable — Phase 5 installs no external packages. All dependencies are Python stdlib or already installed as part of the Home Assistant integration.

---

## Architecture Patterns

### System Architecture Diagram

```
WebSocket command (create_zone / delete_zone / rename_zone / ...)
    │
    ▼
_make_ws_*() factory closure [validates via vol schema]
    │
    ├─► validate_daily_program() [set_zone_time_program only — pre-save gate]
    │
    ├─► CR-01 snapshot = copy.deepcopy(zones) [delete_zone, mutations that touch rooms]
    │
    ├─► mutate runtime_config["zones"] and/or runtime_config["rooms"]
    │
    ├─► store.async_save(runtime_config)  [validate_zone_assignment called inside]
    │      │
    │      ├─ ValueError → rollback snapshot → send_error → return
    │      └─ success → continue
    │
    ├─► connection.send_result(msg["id"], {...})
    │
    └─► hass.async_create_task(coordinator.async_evaluate())
             │
             ▼
    async_evaluate()
         │
         ├─ for each area_id in rooms:
         │    │
         │    ├─ room_config = runtime_config["rooms"].get(area_id, {})
         │    ├─ room_mode = room_config.get("room_mode", "global")
         │    │
         │    ├─ [EVAL-05] if room_mode == ROOM_MODE_CUSTOM → use room.time_program (no change)
         │    ├─ [EVAL-05] if room_mode == ROOM_MODE_FROST  → frost-protection temp (no change)
         │    │
         │    └─ else: resolve zone
         │         │
         │         zone_id = room_config.get("zone_id")
         │         │
         │         ├─ zone_id absent → Default Zone path (global_mode / global_time_program)
         │         │    └─ existing v1.0 evaluation logic (unchanged)
         │         │
         │         └─ zone_id present → Custom Zone path
         │              zone = runtime_config["zones"][zone_id]
         │              │
         │              ├─ zone.mode == off → frost-protection temp (EVAL-01)
         │              ├─ zone.mode == time_program → evaluate_schedule(zone.time_program, now) (EVAL-02)
         │              └─ zone.mode == time_program_presences → compute_occupied_temp(zone.time_program, ...) (EVAL-03)
         │
         └─► _push_safely(entity_id, desired_temp, context)
```

### Recommended Project Structure

No new files required. All changes land in:

```
custom_components/climate_manager/
├── websocket.py     # +6 new _make_ws_*() factories + 6 async_register_command calls
├── coordinator.py   # async_evaluate refactored; zone-aware dispatch added
├── const.py         # No changes expected (zones schema already present from Phase 4)
└── storage.py       # No changes expected (validate_zone_assignment already present)
tests/
├── test_websocket.py  # +6 new WS command tests (zone CRUD, error cases)
└── test_coordinator.py # +N new zone evaluation tests (EVAL-01..05)
```

### Pattern 1: WebSocket Factory (existing — reuse verbatim)

**What:** Each WS command is a nested async function inside a factory closure `_make_ws_*(entry)`. The factory captures `entry` (and thus `entry.runtime_data`) without using `hass.data`.

**When to use:** All 6 new zone commands follow this pattern exactly.

**Example (from existing set_global_mode):**
```python
# Source: custom_components/climate_manager/websocket.py:221-245
def _make_ws_set_global_mode(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_global_mode",
        vol.Required("mode"): vol.In(VALID_MODES),
    })
    @websocket_api.async_response
    async def ws_set_global_mode(hass, connection, msg):
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
    return ws_set_global_mode
```

### Pattern 2: CR-01 Snapshot-Rollback (existing — apply to zone mutations)

**What:** Before mutating runtime_config, snapshot the affected sub-dict with `copy.deepcopy`. If `async_save` raises `ValueError` (from `validate_zone_assignment`), restore the snapshot and send an error.

**When to use:** Required for `delete_zone` (mutates both `zones` and `rooms`). Also apply to any zone command where `validate_zone_assignment` might reject.

**Critical insight:** `delete_zone` must snapshot BOTH `runtime_config["zones"]` AND `runtime_config["rooms"]` before mutation, because the handler modifies both in a single operation (pop zone_id from rooms, del zones[zone_id]).

**Example (from existing set_room_config):**
```python
# Source: custom_components/climate_manager/websocket.py:341-358
rooms_backup = copy.deepcopy(entry.runtime_data.runtime_config.get("rooms", {}))
# ... mutate ...
try:
    await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
except ValueError as exc:
    entry.runtime_data.runtime_config["rooms"] = rooms_backup
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
    return
```

### Pattern 3: validate_daily_program Pre-Save Gate

**What:** For any command that accepts a time program dict, call `validate_daily_program(program)` BEFORE mutating runtime_config. If invalid, send error and return without any mutation or save.

**When to use:** Required for `set_zone_time_program`. The same gate is present in `set_time_program`.

```python
# Source: custom_components/climate_manager/websocket.py:305-313
ok, err = validate_daily_program(msg["program"])
if not ok:
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, err)
    return  # T-03-05: return BEFORE save/evaluate
```

### Pattern 4: Zone Resolution Helper in Coordinator

**What:** A private method `_resolve_zone_config(area_id, config) → (mode, time_program)` avoids duplicating the zone lookup inside both the `_evaluate_time_program` and `_evaluate_time_program_presences` branches.

**When to use:** Called once per room during the evaluation loop, before mode-dispatch.

**Suggested signature:**
```python
def _resolve_zone_config(
    self,
    area_id: str,
    config: dict,
) -> tuple[str, dict]:
    """Return (mode, time_program) for the zone governing this room.

    Default Zone rooms: returns (global_mode, global_time_program).
    Custom zone rooms: returns (zone.mode, zone.time_program).
    Unknown zone_id (referential integrity error): logs warning, falls back to Default Zone.
    """
    zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
    if zone_id is None:
        return config["global_mode"], config["global_time_program"]
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        _LOGGER.warning("Room %s references unknown zone_id %r — falling back to Default Zone", area_id, zone_id)
        return config["global_mode"], config["global_time_program"]
    return zone["mode"], zone["time_program"]
```

### Pattern 5: Per-Room Zone-Aware Dispatch in async_evaluate

**What:** The current top-level `if global_mode == MODE_OFF / elif MODE_TIME_PROGRAM / elif MODE_TIME_PROGRAM_PRESENCES` branch that applies to ALL rooms must be replaced. The new structure evaluates each room individually by resolving its zone first.

**Restructure approach:** The two existing private methods (`_evaluate_time_program`, `_evaluate_time_program_presences`) contain the per-room iteration logic. Rather than gutting them, the cleanest refactor is to:

1. Keep them but rename their role: they now accept `(mode, time_program)` arguments that come from zone resolution, not from `config["global_mode"]`/`config["global_time_program"]` directly.
2. Or: inline the zone-dispatch loop into a new `_evaluate_zone_rooms` method called for each zone in turn.
3. Or: flatten `async_evaluate` into a single per-room loop with zone resolution inline.

**Recommended approach (simpler):** A single per-room loop in `async_evaluate` that calls `_resolve_zone_config` per room, then dispatches based on the resolved mode. This avoids splitting the status tracking (`_last_active_period`, `_last_present_persons`, `_last_room_periods`) across two methods. The existing `_evaluate_time_program` and `_evaluate_time_program_presences` become dead code and should be removed.

**Key:** `_last_active_period` must now be set per-zone or per-room. The existing single `_last_active_period` scalar was for the global program. With zones, the status payload should track per-room periods via `_last_room_periods` (already per-room). `_last_active_period` can default to the Default Zone's active period for backwards compatibility with existing `get_status` consumers.

### Anti-Patterns to Avoid

- **Reading `global_mode` as system-wide switch in the new evaluation loop:** After the refactor, `global_mode` is only consulted for rooms whose zone resolution returns the Default Zone. Custom zone rooms must never read `global_mode`.
- **Skipping the `ROOM_MODE_FROST` / `ROOM_MODE_CUSTOM` check before zone resolution:** Room-level mode (EVAL-05) must short-circuit BEFORE zone resolution. The existing room_mode branch at lines 203-223 in coordinator.py must remain the outermost check.
- **Mutating `DEFAULT_CONFIG` via zone operations:** `create_zone` must deepcopy `global_time_program` from `runtime_config`, never from `DEFAULT_CONFIG`. The `DEFAULT_CONFIG["zones"]` is deliberately empty; zone write handlers must never source zone defaults from `DEFAULT_CONFIG`.
- **Saving with `zone_id` still on rooms before deleting the zone entry:** `delete_zone` must pop `zone_id` from all affected rooms BEFORE calling `store.async_save`. Otherwise `validate_zone_assignment` will raise because the rooms reference a now-deleted zone.
- **Writing explicit `zone_id: null`:** `storage.py:validate_zone_assignment` raises `ValueError` for explicit null. `delete_zone` must `pop("zone_id")` (removes the key entirely), not `room["zone_id"] = None`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom ID scheme | `str(uuid.uuid4())` | stdlib, collision-free, already used in storage.py comments |
| Daily program validation | Inline key checks | `validate_daily_program()` from schedule.py | Already handles missing/extra day keys; tested |
| Zone assignment validation | Inline referential checks | `validate_zone_assignment()` in storage.py | Called inside `async_save` automatically; already tested |
| WS error responses | Direct send_message | `connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))` | Standard HA WS error format |
| Presence evaluation | Any new presence logic | `_compute_present_persons` + `compute_occupied_temp` + `resolve_presence` | These handle all person modes (ha, scheduled, force_present, force_absent) correctly |

---

## Common Pitfalls

### Pitfall 1: delete_zone leaves rooms with dangling zone_id before save

**What goes wrong:** Handler deletes `runtime_config["zones"][zone_id]` first, then tries to save. `validate_zone_assignment` inside `async_save` sees rooms still referencing the now-absent zone and raises `ValueError`. The zone entry was already deleted from runtime_config, leaving it in a corrupt in-memory state.

**Why it happens:** Ordering error — zone deletion and room migration must both complete before save.

**How to avoid:** The correct order is:
1. Snapshot both `zones` and `rooms` (CR-01)
2. Pop `zone_id` from all affected rooms
3. `del runtime_config["zones"][zone_id]`
4. Call `store.async_save()` once after both mutations
5. On `ValueError`, restore both snapshots

**Warning signs:** Test where delete_zone is called with rooms in the zone — if it raises `ValueError` from storage rather than returning success, the ordering is wrong.

### Pitfall 2: reset_zone_time_program target='global' sharing a list reference

**What goes wrong:** `runtime_config["zones"][zone_id]["time_program"] = runtime_config["global_time_program"]` (without deepcopy) causes the zone and global programs to share the same dict and list objects. Subsequent mutation of one affects the other.

**Why it happens:** `reset_zone_time_program(target='global')` copies from global_time_program. The handler must use `copy.deepcopy()` identically to how `reset_time_program` uses it.

**How to avoid:** Always `copy.deepcopy(runtime_config["global_time_program"])`, never direct assignment.

### Pitfall 3: rename_zone for Default Zone — wrong key updated

**What goes wrong:** Handler routes `zone_id == "default"` to update `runtime_config["zones"]["default"]["name"]` (wrong — the Default Zone has no `zones` entry). The stored name remains unchanged.

**Why it happens:** The handler doesn't check the sentinel before performing a generic zones-dict update.

**How to avoid:** Explicit `if zone_id == "default": runtime_config["default_zone_name"] = msg["name"]` BEFORE the general zones-dict path. Never attempt `runtime_config["zones"]["default"]`.

### Pitfall 4: Coordinator reads global_mode for custom zone rooms after refactor

**What goes wrong:** After restructuring `async_evaluate`, a code path in the per-room loop falls through to reading `config["global_mode"]` as the mode for a room that belongs to a custom zone. If `global_mode=off`, all custom zone rooms receive frost-protection even though their zone is in `time_program` mode. This violates D-07/D-08.

**Why it happens:** The old top-level `if global_mode == MODE_OFF` branch (coordinator.py:111-125) must be completely removed. If any remnant of it survives refactoring, it can override the per-zone dispatch.

**How to avoid:** The new `async_evaluate` must NOT have any top-level branch on `global_mode`. Zone resolution is always per-room. The Default Zone path reads `global_mode`; the custom zone path reads `zone["mode"]`.

### Pitfall 5: create_zone initializes time_program from DEFAULT_CONFIG rather than current global program

**What goes wrong:** `create_zone` uses `copy.deepcopy(DEFAULT_CONFIG["global_time_program"])` (the module-level constant) instead of `copy.deepcopy(runtime_config["global_time_program"])` (the user's actual current program). If the user has customized their global schedule, the new zone gets the factory-default schedule instead.

**Why it happens:** Confusion between the constant default and the live config.

**How to avoid:** D-02: always `copy.deepcopy(entry.runtime_data.runtime_config["global_time_program"])`.

### Pitfall 6: set_zone_time_program validates AFTER mutating runtime_config

**What goes wrong:** Handler updates `runtime_config["zones"][zone_id]["time_program"] = msg["program"]` before calling `validate_daily_program`. An invalid program gets written to runtime_config even though the WS handler sends an error response. The next coordinator evaluation uses the invalid program.

**Why it happens:** Validation placed after mutation (wrong order).

**How to avoid:** Mirror `set_time_program` exactly — validate first, return on error, only mutate if valid.

### Pitfall 7: status payload `_last_active_period` becomes ambiguous post-refactor

**What goes wrong:** `_last_active_period` is a scalar that the `get_status` and `subscribe_status` handlers expose as the "current active period" for the global view. After the refactor, there is no single active period — each zone has its own. If the coordinator clears or leaves `_last_active_period` as `None`, the panel's global status indicator shows nothing.

**How to avoid:** After the refactor, set `_last_active_period` to the Default Zone's evaluated period (consistent with v1.0 semantics for the Global Settings tab). The `_last_room_periods` dict already tracks per-room periods and is used by the Rooms tab. This dual approach (scalar for global, dict for rooms) is what the existing `_build_status_payload` and `get_status` handler already expect.

### Pitfall 8: EVAL-04 misread as cross-zone presence propagation

**What goes wrong:** Implementing EVAL-04 as: "when `global_mode=time_program_presences`, apply presence override to rooms in ALL zones regardless of their zone.mode." This contradicts D-10 and violates D-07 (zone independence).

**How to avoid:** EVAL-04 applies only to Default Zone rooms. The REQUIREMENTS.md wording ("regardless of zone mode") is superseded by D-10 from CONTEXT.md. Custom zone rooms in mode=time_program_presences get presence independently via their own zone evaluation. Custom zone rooms NOT in presence mode are unaffected by global_mode.

---

## Code Examples

### create_zone handler skeleton

```python
# Source: pattern derived from existing websocket.py factories + const.py zone schema
import uuid

def _make_ws_create_zone(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/create_zone",
        vol.Required("name"): str,
    })
    @websocket_api.async_response
    async def ws_create_zone(hass, connection, msg):
        zone_id = str(uuid.uuid4())
        runtime_config = entry.runtime_data.runtime_config
        new_zone = {
            "name": msg["name"],
            "mode": MODE_TIME_PROGRAM,  # D-01: defaults to time_program
            "time_program": copy.deepcopy(runtime_config["global_time_program"]),  # D-02
        }
        runtime_config.setdefault("zones", {})[zone_id] = new_zone
        await entry.runtime_data.store.async_save(runtime_config)
        connection.send_result(msg["id"], {
            "zone_id": zone_id,        # D-03: return full zone config
            "name": new_zone["name"],
            "mode": new_zone["mode"],
            "time_program": new_zone["time_program"],
        })
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
    return ws_create_zone
```

### delete_zone handler skeleton (CR-01 ordering)

```python
# Source: pattern derived from set_room_config CR-01 in websocket.py:341-358
def _make_ws_delete_zone(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/delete_zone",
        vol.Required("zone_id"): str,
    })
    @websocket_api.async_response
    async def ws_delete_zone(hass, connection, msg):
        runtime_config = entry.runtime_data.runtime_config
        zone_id = msg["zone_id"]
        # Guard: cannot delete Default Zone (no entry in zones dict anyway)
        if zone_id not in runtime_config.get("zones", {}):
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, f"Zone {zone_id!r} not found")
            return
        # CR-01: snapshot both zones and rooms before any mutation
        zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
        rooms_backup = copy.deepcopy(runtime_config.get("rooms", {}))
        # Step 1: migrate rooms — pop zone_id (sparse model: absent = Default Zone)
        for room_cfg in runtime_config.get("rooms", {}).values():
            if room_cfg.get("zone_id") == zone_id:
                room_cfg.pop("zone_id", None)  # D-06: do NOT set zone_id: None
        # Step 2: remove the zone entry
        del runtime_config["zones"][zone_id]
        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except ValueError as exc:
            runtime_config["zones"] = zones_backup
            runtime_config["rooms"] = rooms_backup
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
            return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
    return ws_delete_zone
```

### Coordinator zone-aware dispatch (per-room loop sketch)

```python
# Source: derived from coordinator.py _evaluate_time_program (lines 174-232)
# and _evaluate_time_program_presences (lines 234-365)
async def async_evaluate(self, _utc_now=None):
    now = dt_util.now()
    config = self._data.runtime_config
    period_temperatures = config["period_temperatures"]
    rooms = self._data.rooms

    present_persons = self._compute_present_persons(config, now)
    self._last_present_persons = present_persons
    present_set = set(present_persons)
    present_locked_rooms: set[str] = set()

    desired_temps: dict[str, float] = {}
    room_periods: dict[str, str] = {}

    for area_id in rooms:
        room_config = config.get("rooms", {}).get(area_id, {})
        room_mode = room_config.get("room_mode", ROOM_MODE_GLOBAL)

        # EVAL-05: room-level overrides always win before zone resolution
        if room_mode == ROOM_MODE_FROST:
            desired_temps[area_id] = period_temperatures[PERIOD_FROST_PROTECTION]
            room_periods[area_id] = PERIOD_FROST_PROTECTION
            continue
        if room_mode == ROOM_MODE_CUSTOM:
            custom_program = room_config.get("time_program") or config["global_time_program"]
            period_mode = evaluate_schedule(custom_program, now)
            desired_temps[area_id] = period_temperatures.get(period_mode, period_temperatures[PERIOD_FROST_PROTECTION])
            room_periods[area_id] = period_mode
            continue  # custom rooms skip presence override below

        # Zone resolution (D-09)
        zone_mode, zone_time_program = self._resolve_zone_config(area_id, config)

        if zone_mode == MODE_OFF:
            # EVAL-01
            desired_temps[area_id] = period_temperatures[PERIOD_FROST_PROTECTION]
            room_periods[area_id] = PERIOD_FROST_PROTECTION
        elif zone_mode == MODE_TIME_PROGRAM:
            # EVAL-02
            period_mode = evaluate_schedule(zone_time_program, now)
            desired_temps[area_id] = period_temperatures.get(period_mode, period_temperatures[PERIOD_FROST_PROTECTION])
            room_periods[area_id] = period_mode
        elif zone_mode == MODE_TIME_PROGRAM_PRESENCES:
            # EVAL-03: baseline from zone schedule
            period_mode = evaluate_schedule(zone_time_program, now)
            desired_temps[area_id] = period_temperatures.get(period_mode, period_temperatures[PERIOD_FROST_PROTECTION])
            room_periods[area_id] = period_mode
            # Presence override applied in second pass below

    # Second pass: presence overrides for rooms with zone=time_program_presences
    # (and Default Zone rooms when global_mode=time_program_presences)
    # ... [mirror existing _evaluate_time_program_presences person loop] ...

    self._last_room_periods = room_periods
    # Set _last_active_period to Default Zone's period for backwards compatibility (Pitfall 7)
    default_zone_period = evaluate_schedule(config["global_time_program"], now)
    self._last_active_period = default_zone_period if config["global_mode"] != MODE_OFF else None

    await asyncio.gather(*(
        self._push_safely(eid, desired_temps[area_id], "ZONE_EVAL")
        for area_id, entity_ids in rooms.items()
        for eid in entity_ids
        if area_id in desired_temps and is_trv_entity(self._hass, eid)
    ))
    self._hass.bus.async_fire(f"{DOMAIN}_status_update", self._build_status_payload())
```

---

## State of the Art

| Old Approach | Current Approach | Changed | Impact |
|--------------|------------------|---------|--------|
| `global_mode` as system-wide override for all rooms | `global_mode` = Default Zone's mode only; custom zone rooms are independent | Phase 5 refactor | Coordinator `async_evaluate` top-level branch on `global_mode` must be removed |
| Single `_last_active_period` scalar for all rooms | `_last_room_periods` dict (already per-room); `_last_active_period` = Default Zone period | Phase 3 already introduced `_last_room_periods`; Phase 5 must continue this | No status payload format change needed |
| No zone concept in storage | `zones: {}` in DEFAULT_CONFIG; `zone_id` on room entries | Phase 4 (completed) | Phase 5 can read zone data immediately |

**Deprecated / to be removed:**
- The top-level `if global_mode == MODE_OFF` / `elif MODE_TIME_PROGRAM` / `elif MODE_TIME_PROGRAM_PRESENCES` branch in `async_evaluate` — replaced by per-room zone dispatch.
- The `_evaluate_time_program` and `_evaluate_time_program_presences` methods as standalone methods — their logic is inlined into the unified per-room loop or refactored to accept `(mode, time_program)` arguments.

---

## Open Questions

1. **`_evaluate_time_program` / `_evaluate_time_program_presences` refactor strategy**
   - What we know: both methods implement per-room iteration with room_mode short-circuits; their logic is correct but reads `config["global_mode"]`/`config["global_time_program"]` directly.
   - What's unclear: whether to (a) delete both methods and inline a unified loop, or (b) keep them and add `zone_mode`/`zone_program` parameters.
   - Recommendation: Option (a) — a single unified loop in `async_evaluate` is simpler to reason about and avoids the status-tracking (`_last_active_period`, `_last_present_persons`) being split across two methods. The planner should choose this approach and document it in the plan.

2. **Presence override pass: single-pass vs. two-pass for mixed zone modes**
   - What we know: the existing `_evaluate_time_program_presences` uses a two-pass algorithm (baseline first, then presence override). The same pattern is needed for custom zones with mode=time_program_presences.
   - What's unclear: with a unified per-room loop, ROOM_MODE_CUSTOM rooms skip the presence pass via `continue`. Rooms with zone=time_program_presences and rooms with zone=time_program are in the same iteration. A single-pass approach requires identifying "presence-eligible rooms" upfront.
   - Recommendation: keep the two-pass structure (baseline dict first, then person iteration for presence-eligible rooms). The `frost_locked_rooms` set from the existing presences method becomes redundant because ROOM_MODE_FROST already `continue`s before zone resolution; remove it.

3. **`_build_status_payload` and zone awareness**
   - What we know: `_build_status_payload` returns `global_mode` at the top level, which the panel's Global Settings tab displays. After the refactor, `global_mode` is the Default Zone's mode — this field name remains semantically correct for the Default Zone tab.
   - What's unclear: whether `rooms_status` entries should include a `zone_id` field for the panel to display zone badges.
   - Recommendation: Out of scope for Phase 5 (no frontend UI). The status payload format is unchanged. Zone badge display is Phase 6 work. If the planner needs to add `zone_id` to `rooms_status` for Phase 6 forward-compatibility, it is low-risk but optional.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component |
| Config file | `pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/test_coordinator.py tests/test_websocket.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ZONE-05 | create_zone returns full zone object with generated UUID | integration | `uv run pytest tests/test_websocket.py::test_ws_create_zone_returns_zone_config -x` | ❌ Wave 0 |
| ZONE-05 | create_zone initializes time_program from current global_time_program (D-02) | integration | `uv run pytest tests/test_websocket.py::test_ws_create_zone_copies_global_program -x` | ❌ Wave 0 |
| ZONE-06 | rename_zone updates zones[zone_id].name for custom zone | integration | `uv run pytest tests/test_websocket.py::test_ws_rename_zone_custom -x` | ❌ Wave 0 |
| ZONE-06 | rename_zone with zone_id="default" updates default_zone_name (not zones dict) | integration | `uv run pytest tests/test_websocket.py::test_ws_rename_zone_default -x` | ❌ Wave 0 |
| ZONE-07 | delete_zone migrates rooms to Default Zone (pop zone_id) | integration | `uv run pytest tests/test_websocket.py::test_ws_delete_zone_migrates_rooms -x` | ❌ Wave 0 |
| ZONE-07 | delete_zone on non-existent zone_id returns ERR_NOT_FOUND | integration | `uv run pytest tests/test_websocket.py::test_ws_delete_zone_not_found -x` | ❌ Wave 0 |
| ZONE-08 | set_zone_mode updates zone.mode; invalid mode rejected by schema | integration | `uv run pytest tests/test_websocket.py::test_ws_set_zone_mode -x` | ❌ Wave 0 |
| ZONE-09 | set_zone_time_program validates program before save (partial program rejected) | integration | `uv run pytest tests/test_websocket.py::test_ws_set_zone_time_program_rejects_partial -x` | ❌ Wave 0 |
| ZONE-09 | reset_zone_time_program target='default' restores factory schedule | integration | `uv run pytest tests/test_websocket.py::test_ws_reset_zone_time_program_default -x` | ❌ Wave 0 |
| ZONE-09 | reset_zone_time_program target='global' deep-copies global_time_program | integration | `uv run pytest tests/test_websocket.py::test_ws_reset_zone_time_program_global -x` | ❌ Wave 0 |
| EVAL-01 | Zone mode=off → rooms in that zone receive frost-protection temp | integration | `uv run pytest tests/test_coordinator.py::test_zone_mode_off_pushes_frost_temp -x` | ❌ Wave 0 |
| EVAL-02 | Zone mode=time_program → rooms follow zone.time_program, not global | integration | `uv run pytest tests/test_coordinator.py::test_zone_mode_time_program_uses_zone_schedule -x` | ❌ Wave 0 |
| EVAL-03 | Zone mode=time_program_presences → present person overrides zone schedule | integration | `uv run pytest tests/test_coordinator.py::test_zone_mode_presences_applies_presence -x` | ❌ Wave 0 |
| EVAL-04 | Default Zone with global_mode=off does NOT affect custom zone rooms | integration | `uv run pytest tests/test_coordinator.py::test_global_mode_off_does_not_affect_custom_zones -x` | ❌ Wave 0 |
| EVAL-05 | Room with room_mode=custom ignores zone mode/schedule | integration | `uv run pytest tests/test_coordinator.py::test_room_mode_custom_wins_over_zone -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_coordinator.py tests/test_websocket.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

All test functions listed above are new — none exist yet. The test infra (`conftest.py`, `hass` fixture, `MockConfigEntry`, `hass_ws_client`) is fully in place and requires no additions. Wave 0 must create all test functions in:

- [ ] `tests/test_websocket.py` — 10 new zone CRUD command tests
- [ ] `tests/test_coordinator.py` — 5 new zone evaluation tests

The helper `_make_runtime_config` in `test_coordinator.py` needs a `zones_config` parameter added to support seeding custom zones in coordinator tests.

---

## Security Domain

Zone operations do not introduce new attack surfaces beyond those already covered by the existing WebSocket API security model.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | HA WebSocket auth gate handles this (T-03-06) |
| V3 Session Management | no | HA manages sessions |
| V4 Access Control | no | Panel access = HA user auth; no per-zone ACL in v1.1 |
| V5 Input Validation | yes | `vol.In(VALID_MODES)` schema gate + `validate_daily_program` pre-save gate |
| V6 Cryptography | no | No crypto in zone operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Zone_id injection (client sends crafted zone_id referencing non-existent zone) | Tampering | `vol.Coerce(str)` in schema; `validate_zone_assignment` in `async_save` raises ValueError |
| Explicit zone_id: null bypassing sparse model | Tampering | `validate_zone_assignment` rejects explicit null (storage.py:48-52) |
| Large time_program payload (DoS) | DoS | `validate_daily_program` validates structure; HA WebSocket message size limits apply |
| rename_zone targeting "default" to bypass zones-dict guard | Tampering | D-05 sentinel check routes to `default_zone_name` field; zones dict is never accessed for "default" |

---

## Sources

### Primary (HIGH confidence — code verified in this session)

- `custom_components/climate_manager/websocket.py` — all 11 existing WS handlers; factory pattern; CR-01 rollback; vol schema patterns; write-then-evaluate
- `custom_components/climate_manager/coordinator.py` — complete evaluation engine; `_evaluate_time_program`, `_evaluate_time_program_presences`, `_compute_present_persons`, `_build_status_payload`
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG`, `VALID_MODES`, `_DEFAULT_DAILY_PROGRAM`, `PERIOD_FROST_PROTECTION`, zone schema comment block
- `custom_components/climate_manager/storage.py` — `validate_zone_assignment`, `async_save` hook, CR-02 comment, sparse-merge logic
- `custom_components/climate_manager/schedule.py` — `evaluate_schedule`, `compute_occupied_temp`, `validate_daily_program`, `resolve_presence`
- `.planning/phases/05-zone-crud-evaluation-engine/05-CONTEXT.md` — all locked decisions D-01..D-12
- `.planning/phases/04-zone-data-model-storage/04-CONTEXT.md` — foundational zone model decisions D-01..D-07
- `tests/test_coordinator.py` — test infrastructure patterns; `_make_runtime_config` helper; `_make_simple_coordinator`; freeze_time usage; service mock patterns
- `tests/test_websocket.py` — WebSocket test patterns; `_setup_entry` helper; `hass_ws_client` usage

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — ZONE-05..09, EVAL-01..05 (EVAL-04 interpretation superseded by D-10)
- `.planning/ROADMAP.md` — Phase 5 success criteria (5 behavioural scenarios)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pytest-homeassistant-custom-component` is installed in the project's test venv (not in system Python) | Validation Architecture | Tests would not collect; low risk — project CI is already passing per git log |
| A2 | `uv run pytest` is the correct invocation in this project (not bare `pytest`) | Validation Architecture | Low risk — `uv` is confirmed as the package manager from CLAUDE.md; adjust if needed |

**If this table is empty of high-risk items:** all critical claims were verified directly from the source code read in this session.

---

## Metadata

**Confidence breakdown:**

- WebSocket handler patterns: HIGH — all existing handlers read in full; new handlers are mechanical copies
- Coordinator evaluation refactor: HIGH — full coordinator.py read; refactor strategy is unambiguous
- Test infrastructure: HIGH — conftest.py, test_coordinator.py, test_websocket.py all read; patterns are clear
- Edge cases (delete_zone ordering, rename_zone sentinel, deepcopy requirements): HIGH — derived from code analysis of storage.py validate_zone_assignment and existing CR-01 pattern

**Research date:** 2026-05-27
**Valid until:** Stable (no external dependencies; only changes if project code changes)

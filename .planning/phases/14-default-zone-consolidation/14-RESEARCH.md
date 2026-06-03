# Phase 14: Default Zone Consolidation - Research

**Researched:** 2026-06-03
**Domain:** Python config schema refactor + HA WebSocket API + TypeScript frontend
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config Schema (D-01)**
`DEFAULT_CONFIG` replaces 4 flat keys with a single `default_zone` key
shaped as a full `ZoneConfig`:
```python
"default_zone": {
    "name": "Home",
    "mode": DEFAULT_GLOBAL_MODE,
    "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "preheat_enabled": False,
}
```
Old flat keys (`global_mode`, `global_time_program`, `default_zone_name`,
`default_zone_preheat_enabled`) are absent from `DEFAULT_CONFIG`.

**Storage Migration (D-02/D-03)**
Lazy read-time compat shim in `storage.py`. On every load, if old format is
detected (`global_mode` present, `default_zone` absent), build `default_zone`
in memory from the flat keys. No write-back. Existing day-fill logic moves
inside the shim and applies to `default_zone["time_program"]` in both legacy
and new-format paths.

**Coordinator (D-04/D-05/D-06/D-07)**
`_resolve_zone_config` removes Default Zone special-case. Adds
`_last_zone_periods: dict[str, str | None]`. `_build_status_payload` removes
`global_mode`/`active_period`, adds `zones: dict`. `ws_get_status` delegates
to `coordinator._build_status_payload()`.

**WebSocket Commands (D-08/D-09/D-10/D-11)**
Remove `set_global_mode` and `reset_time_program`. Extend `set_zone_mode` and
`reset_zone_time_program` to handle `zone_id="default"`. Rename
`reset_room_to_global_program` → `reset_room_to_default_zone_program`.
Update `set_zone_preheat` and `rename_zone` internal paths.

**Frontend (D-12/D-13/D-14/D-15/D-16)**
`ClimateConfig` interface: remove 4 flat keys, add `default_zone: ZoneConfig`.
`StatusPayload`: remove `global_mode`/`active_period`, add
`zones: Record<string, { mode, active_period }>`. `main.ts` removes synthesis
block (lines 509–512), passes `config.default_zone` directly. Component
read-path updates throughout. `ws-client.ts` removes `setGlobalMode()` and
`resetRoomToGlobalProgram()`, adds updated paths.

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- `room_mode: custom` removal — Phase 15
- Per-zone boiler declaration, demand control — v1.4+
- Full `get_status` → `get_zone_status` rename (command type string unchanged)
- Multi-language labels
- Phase 15+ observability / logging
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-01 | Default Zone stored as a first-class `ZoneConfig` under a single `default_zone` key; `global_mode`, `global_time_program`, `default_zone_name`, and `default_zone_preheat_enabled` flat keys removed and migrated on load | Full implementation map in Standard Stack and Architecture Patterns sections |
</phase_requirements>

---

## Summary

Phase 14 is a pure refactoring phase — no new user-facing features, no new
external dependencies. The entire work is a schema migration: the Default Zone
currently lives as four scattered flat keys in `DEFAULT_CONFIG` and in every
layer that reads or writes config. This phase collapses those four keys into a
single `default_zone: ZoneConfig` entry that is structurally identical to how
custom zones are already stored under `config["zones"][uuid]`.

The migration is low-risk because the new shape is already proven by the custom
zone code path, which has been in production since Phase 5. The compat shim
pattern (`"global_mode" in result and "default_zone" not in result`) is the
same lazy-read approach used successfully in phases 9 and 12 (person mode
renames, preheat_lead_minutes rename, GAP-01 room→zone preheat migration). No
write-back is required on load — the new format is persisted naturally on the
first mutation.

The frontend portion is the widest surface of this change: seven files
(`types.ts`, `main.ts`, `global-settings-tab.ts`, `room-card.ts`,
`zone-tab.ts`, `ws-client.ts`) all reference the old flat keys, but the
substitutions are mechanical find-and-replace style changes guided by the exact
line numbers in CONTEXT.md. The WebSocket contract changes (two commands
removed, two extended, one renamed) require both backend and frontend to update
in lockstep within the same phase.

**Primary recommendation:** Implement backend (const + storage + coordinator
+ websocket) before frontend so the new WS contract is stable when frontend
changes are applied. Run the full test suite after each wave.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Config schema (`DEFAULT_CONFIG`) | Backend (const.py) | — | Single source of truth for schema shape |
| Storage migration shim | Backend (storage.py) | — | Read-time normalization, no HA core involvement |
| Zone resolution logic | Backend (coordinator.py) | — | Evaluation engine reads config directly |
| Status payload construction | Backend (coordinator.py) | — | `_build_status_payload` already owns this |
| WebSocket command registry | Backend (websocket.py) | — | Commands registered in `async_register_commands` |
| Config + status type interfaces | Frontend (types.ts) | — | Canonical TypeScript shape consumed by all components |
| Zone data synthesis / passing | Frontend (main.ts) | — | Passes zoneConfig object to zone-tab |
| Zone mode display and mutation | Frontend (zone-tab.ts) | ws-client.ts | zone-tab calls ws.setZoneMode / ws.resetZoneTimeProgram |
| Global settings display | Frontend (global-settings-tab.ts) | — | Reads Default Zone name/mode from config.default_zone |
| Room-card mode badge | Frontend (room-card.ts) | — | Reads zone mode from status.zones["default"] |
| WS command wrappers | Frontend (ws-client.ts) | — | Maps method calls to WS message types |

---

## Standard Stack

This phase installs no new packages. All implementation uses code already
present in the project.

### Core (existing, no new installs)

| Library | Version | Purpose |
|---------|---------|---------|
| Python 3.12 | project-required | Integration language |
| `homeassistant.helpers.storage.Store` | HA 2025.x | Persistent config (unchanged) |
| `homeassistant.components.websocket_api` | HA 2025.x | WS command registration (unchanged) |
| Lit 3.x | project-required | Frontend panel components |
| TypeScript 5.x | project-required | Type-safe frontend |

### Installation

No new packages — phase is a pure refactoring.

---

## Package Legitimacy Audit

No packages are installed in this phase.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Storage on disk (old format)          Storage on disk (new format)
  global_mode: "time_program"    OR     default_zone:
  global_time_program: {...}               name: "Home"
  default_zone_name: "Home"                mode: "time_program"
  default_zone_preheat_enabled: F          time_program: {...}
                                           preheat_enabled: false
          |                                        |
          |  async_load() compat shim              |  direct read
          v                                        v
   runtime_config["default_zone"] = {name, mode, time_program, preheat_enabled}
          |
          +---> coordinator._resolve_zone_config(area_id, config)
          |       if zone_id is None → config["default_zone"]["mode/time_program"]
          |       else              → config["zones"][zone_id]["mode/time_program"]
          |
          +---> coordinator._build_status_payload()
          |       "zones": {
          |         "default": {mode, active_period},
          |         <uuid>:    {mode, active_period}, ...
          |       }
          |
          v
   ws_get_status  → delegates to coordinator._build_status_payload()
   subscribe_status push → same payload
          |
          v
   Frontend types.ts
     ClimateConfig.default_zone: ZoneConfig
     StatusPayload.zones: Record<string, {mode, active_period}>
          |
          +---> main.ts: passes config.default_zone directly to zone-tab
          +---> global-settings-tab: reads config.default_zone.name/mode
          +---> room-card: reads status.zones["default"].mode
          +---> zone-tab: reads zoneConfig.time_program (unchanged interface)
          +---> ws-client: setZoneMode("default", mode)
                            resetZoneTimeProgram("default", "default")
                            resetRoomToDefaultZoneProgram(roomId)
```

### Recommended Project Structure

No structural changes to the project layout. Modified files only:

```
custom_components/climate_manager/
├── const.py          # DEFAULT_CONFIG — replace 4 flat keys with default_zone
├── storage.py        # async_load() — add compat shim before return
├── coordinator.py    # _resolve_zone_config, async_evaluate, _build_status_payload
└── websocket.py      # remove 2 commands, extend 2, rename 1, update 2

frontend/src/
├── types.ts          # ClimateConfig, StatusPayload interfaces
├── main.ts           # remove synthesis block (lines 509–512)
├── ws-client.ts      # remove setGlobalMode(), rename resetRoomToGlobal*
└── components/
    ├── global-settings-tab.ts   # 2 read-path substitutions
    ├── room-card.ts             # 5 read-path substitutions
    └── zone-tab.ts              # 2 read-path substitutions
```

### Pattern 1: Lazy Read-Time Compat Shim

**What:** Detect old-format storage on load; build new in-memory shape from
old keys. No write-back to disk. Old configs silently upgrade on first
mutation.

**When to use:** Any storage migration where backward compatibility with
existing user configs is required and in-place disk upgrade is not worth
the risk.

**Insertion point:** `storage.py:async_load()`, after the existing post-merge
fill logic and person-mode migrations, before `return result`.

**Example (from CONTEXT.md D-02/D-03):**
```python
# Source: 14-CONTEXT.md D-02, D-03
# Insert in storage.py async_load() after existing migrations

# Phase 14 compat shim: promote old flat keys to default_zone sub-dict.
# Guard: old format has global_mode present AND default_zone absent.
if "global_mode" in result and "default_zone" not in result:
    # Day-fill pass: seed any day with [] before building default_zone
    time_program = result.get("global_time_program", {})
    for day, periods in time_program.items():
        if not periods:
            time_program[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])
    result["default_zone"] = {
        "name": result.pop("default_zone_name", "Home"),
        "mode": result.pop("global_mode"),
        "time_program": result.pop(
            "global_time_program",
            copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
        ),
        "preheat_enabled": result.pop(
            "default_zone_preheat_enabled", False
        ),
    }
else:
    # New format: still run day-fill on default_zone["time_program"]
    time_program = result.get("default_zone", {}).get("time_program", {})
    for day, periods in time_program.items():
        if not periods:
            time_program[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])
```

**Key detail:** The guard `"global_mode" in result and "default_zone" not in
result` is explicit to avoid false-positives on new-format configs. [ASSUMED]

### Pattern 2: zone_id="default" Sentinel Extension

**What:** Extend handlers that already have `zone_id="default"` sentinel
branching to read/write `runtime_config["default_zone"][key]` instead of
`runtime_config["default_zone_name"]` or `runtime_config[key]`.

**Already implemented in:** `rename_zone` (D-05 line 815), `set_zone_preheat`
(line 928).

**To extend:** `set_zone_mode`, `reset_zone_time_program`.

**Example (set_zone_mode extension from D-08):**
```python
# Source: 14-CONTEXT.md D-08 + existing set_zone_mode pattern
async def ws_set_zone_mode(...):
    runtime_config = entry.runtime_data.runtime_config
    if msg["zone_id"] == "default":
        old_val = runtime_config["default_zone"].get("mode")
        runtime_config["default_zone"]["mode"] = msg["mode"]
        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except Exception as exc:
            runtime_config["default_zone"]["mode"] = old_val
            connection.send_error(...)
            return
    else:
        # existing custom zone path unchanged
        if msg["zone_id"] not in runtime_config.get("zones", {}):
            ...
```

### Pattern 3: _resolve_zone_config Simplification

**What:** Remove the `if zone_id is None` special-case that reads from
`config["global_mode"]` / `config["global_time_program"]`. Replace with
`config["default_zone"]["mode"]` / `config["default_zone"]["time_program"]`.

**Current code (coordinator.py lines 1315–1334):**
```python
def _resolve_zone_config(self, area_id, config):
    zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
    if zone_id is None:
        return (config["global_mode"], config["global_time_program"])  # REMOVE
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        _LOGGER.warning(...)
        return (config["global_mode"], config["global_time_program"])  # REMOVE
    return (zone["mode"], zone["time_program"])
```

**After (D-04):**
```python
def _resolve_zone_config(self, area_id, config):
    zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
    if zone_id is None:
        dz = config["default_zone"]
        return (dz["mode"], dz["time_program"])
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        _LOGGER.warning(...)
        dz = config["default_zone"]
        return (dz["mode"], dz["time_program"])
    return (zone["mode"], zone["time_program"])
```

### Pattern 4: _build_status_payload New Shape

**What:** Replace `global_mode` + `active_period` top-level keys with a
`zones` dict keyed by `"default"` and UUID strings.

**New structure (D-06):**
```python
return {
    "zones": {
        "default": {
            "mode": config["default_zone"]["mode"],
            "active_period": self._last_zone_periods.get("default"),
        },
        **{
            zone_id: {
                "mode": zone["mode"],
                "active_period": self._last_zone_periods.get(zone_id),
            }
            for zone_id, zone in config.get("zones", {}).items()
        },
    },
    "present_persons": self._last_present_persons,
    "rooms_status": rooms_status,
}
```

**`_last_zone_periods` population in `async_evaluate` (D-05):**
Add after `_last_active_period` is set:
```python
# D-05: populate per-zone active periods
dz = config["default_zone"]
self._last_zone_periods = {
    "default": (
        evaluate_schedule(dz["time_program"], now)
        if dz["mode"] != MODE_OFF
        else None
    ),
    **{
        zone_id: (
            evaluate_schedule(zone["time_program"], now)
            if zone["mode"] != MODE_OFF
            else None
        )
        for zone_id, zone in config.get("zones", {}).items()
    },
}
```

### Pattern 5: ws_get_status Delegation (D-07)

**What:** `ws_get_status` duplicates most of `_build_status_payload`. After
the refactor, `ws_get_status` calls `coordinator._build_status_payload()` and
merges the sensor-reads result into it.

**Current ws_get_status** (websocket.py lines 154–271): builds a full
rooms_status list with sensor reads, plus `global_mode` / `active_period` at
the top level.

**After D-07:** The sensor-read block and room-loop in `ws_get_status` are
merged into `_build_status_payload`. `ws_get_status` becomes:
```python
async def ws_get_status(...):
    coordinator = entry.runtime_data.coordinator
    payload = coordinator._build_status_payload()
    connection.send_result(msg["id"], payload)
```

**Important:** `_build_status_payload` already contains the sensor-read loop
(lines 1509–1582). The sensor-read code in `ws_get_status` is a near-duplicate
that must be deleted (not merged again). Verify both implementations are
identical before deleting — they were last synchronised in Phase 12 comment
"D-10 (Pitfall 1 — ws_get_status must match _build_status_payload exactly)".

### Pattern 6: Frontend Optional Chaining Fallback

**What:** `status?.zones?.["default"]?.mode` — use optional chaining
throughout since `zones` is absent during initial load before first push.
Fall back to `config.default_zone.mode` with `??`.

**Example (D-15, same as current `status?.global_mode ?? config.global_mode`):**
```typescript
// Source: 14-CONTEXT.md D-15
const defaultZoneMode =
  this.status?.zones?.["default"]?.mode ?? this.config.default_zone.mode;
```

### Anti-Patterns to Avoid

- **Forgetting the dangling-zone fallback:** `_resolve_zone_config` has two
  `return` paths for Default Zone (None zone_id AND unknown zone_id). Both
  must be updated; missing the second causes a KeyError on dangling zone_id
  if any room still references a deleted zone.

- **`_last_active_period` not removed from `async_evaluate`:** The field
  still exists on the coordinator for backward compatibility with any code
  that reads it externally. However, `_build_status_payload` must stop
  populating `"active_period"` at the top level of the returned dict — or
  the frontend will find both old and new keys and be confused. Check
  `_last_active_period` usages carefully before deleting.

- **`global_time_program` still referenced in `create_zone`:** Line 764 in
  websocket.py does `copy.deepcopy(runtime_config["global_time_program"])`.
  After Phase 14, this key no longer exists. Must change to
  `runtime_config["default_zone"]["time_program"]`.

- **`reset_zone_time_program` "global" target path:** Line 1126 reads
  `runtime_config["global_time_program"]`. After migration, must change to
  `runtime_config["default_zone"]["time_program"]`.

- **`reset_room_to_default_zone_program` reads old key:** Line 721 currently
  reads `runtime_config.get("global_time_program", {})`. Must change to
  `runtime_config["default_zone"]["time_program"]`.

- **Test helper `_make_runtime_config`:** All coordinator and websocket tests
  build runtime_config with `global_mode`, `global_time_program`,
  `default_zone_name` flat keys (test_coordinator.py line 86–105). These test
  helpers must be updated as part of the plan — tests will fail on the first
  run otherwise.

- **`test_load_fresh_install_returns_default_config` will fail:** This test
  asserts `result == DEFAULT_CONFIG`. After DEFAULT_CONFIG changes, the
  test still passes (it compares against the updated DEFAULT_CONFIG). However
  `test_load_fresh_install_includes_zones_and_default_zone_name`
  (test_storage.py line 153) asserts `"default_zone_name" in result` and
  `result["default_zone_name"] == "Home"` — these assertions must be updated
  to check `result["default_zone"]["name"] == "Home"`.

- **`test_load_sparse_stored_data_merges_over_defaults` and related storage
  tests:** Tests that write `{"global_mode": "off"}` to simulate old stored
  data now exercise the compat shim path. After migration, the result must
  have `default_zone["mode"] == "off"` rather than a top-level `global_mode`.
  Existing test (line 43–62) asserts `result["global_mode"] == "off"` — this
  assertion must be updated.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Storage migration detection | Custom version-field bump + migration table | Guard expression in `async_load()` | Simpler; storage version is already 2; a new version would break HACS installs mid-upgrade |
| Write-back on load | Immediate `async_save` in `async_load` | Let first mutation trigger `async_save` | No-write-back avoids HA startup write contention and matches established pattern (phases 9, 12) |
| New WS command for get_status | Rename command type string | Keep `get_status` type string, change payload shape | D-deferred decision from CONTEXT.md; avoids unnecessary WS API churn |
| Manual deep-compare for sensor-read parity | New diff algorithm | Delete ws_get_status sensor-read block; use `_build_status_payload` as single source | `_build_status_payload` already owns sensor reads; maintaining two copies is the bug being fixed |

---

## Runtime State Inventory

This phase is a refactoring that changes stored config key names. Runtime state
analysis applies.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | HA `.storage/climate_manager` JSON file on disk: old format has `global_mode`, `global_time_program`, `default_zone_name`, `default_zone_preheat_enabled` at top level. New format has `default_zone: {name, mode, time_program, preheat_enabled}`. | Lazy compat shim in `storage.py:async_load()` (D-02). No data migration task needed — handled transparently on first read. |
| Live service config | None — this integration does not store state in external services (n8n, Datadog, etc.) | None |
| OS-registered state | None — no scheduled tasks, pm2 processes, or systemd units reference the key names | None |
| Secrets/env vars | None — no env vars reference `global_mode` or the old key names | None |
| Build artifacts | `frontend/` build output in `custom_components/climate_manager/www/panel.js` will be stale after frontend changes. | Rebuild via `make build && make deploy` in the frontend wave |

---

## Common Pitfalls

### Pitfall 1: `create_zone` still references `global_time_program`

**What goes wrong:** `_make_ws_create_zone` (websocket.py line 764) deep-copies
`runtime_config["global_time_program"]` as the seed for a new zone's
`time_program`. After DEFAULT_CONFIG no longer has this key, a fresh install
will raise `KeyError: 'global_time_program'` when creating the first custom
zone.

**Why it happens:** `global_time_program` appears in 3 places in websocket.py
(create_zone seed, reset_zone_time_program "global" target, reset_room_to...
handler) and in 1 place in coordinator.py `async_evaluate`. All four must be
changed.

**How to avoid:** Before closing the websocket.py plan task, grep for
`global_time_program` and `global_mode` in the file — all matches must be
zero after the change.

**Warning signs:** `KeyError: 'global_time_program'` in HA logs when user
creates a zone or resets a zone program.

### Pitfall 2: `_last_active_period` field retained but payload key removed

**What goes wrong:** `_build_status_payload` currently returns `"active_period"` at
the top level. `ws_get_status` also returns it. After Phase 14, neither should
include `"active_period"` as a top-level key. But `_last_active_period` is
still set in `async_evaluate` for use by `_last_room_periods` fallback
(`coordinator._last_room_periods.get(area_id, active_period)` in ws_get_status
and `_build_status_payload`). After the delegation refactor (D-07), the
per-room `active_period` in `rooms_status[i].active_period` is still valid and
unchanged — it is only the top-level `active_period` key that is removed.

**How to avoid:** The `_last_active_period` instance variable can stay on the
coordinator (used as fallback in room_periods dict lookup). Just stop including
`"active_period"` and `"global_mode"` as top-level keys in the return dict of
`_build_status_payload`.

### Pitfall 3: deepcopy on compat shim time_program

**What goes wrong:** If the compat shim assigns
`result["default_zone"]["time_program"] = result.pop("global_time_program")`
without a deepcopy, the dict reference is shared. A later mutation (e.g.,
reset to default) will deepcopy the module constant correctly, but the runtime
`default_zone.time_program` is the same object as what was on disk until the
next load. In practice this only matters if the coordinator and ws handlers
both hold references — they do, via `runtime_config`.

**How to avoid:** The compat shim pops the old key and assigns it directly (no
extra deepcopy needed — pop gives ownership). However, if a deep-copy path
ever reassigns a new dict to `default_zone["time_program"]`, the original is
released correctly. No extra deepcopy needed in the shim itself.

### Pitfall 4: Test helper `_make_runtime_config` not updated

**What goes wrong:** `test_coordinator.py` line 86 builds runtime_config with
old flat keys. After const.py changes, the coordinator reads
`config["default_zone"]` — any test that builds config with the old shape will
raise `KeyError: 'default_zone'` on the first `_resolve_zone_config` or
`_build_status_payload` call.

**How to avoid:** Update `_make_runtime_config` in test_coordinator.py and the
equivalent fixture in test_websocket.py as part of the same wave that changes
coordinator.py and websocket.py.

### Pitfall 5: Frontend optional chaining depth

**What goes wrong:** `status?.zones?.["default"]?.mode` requires 3 levels of
optional chaining. Missing the middle level (`zones`) causes
`TypeError: Cannot read properties of undefined (reading '"default"')` when
status arrives before `zones` is populated.

**How to avoid:** Always use `status?.zones?.["default"]?.mode` (never
`status?.zones["default"]?.mode`) — the bracket access without `?.` on the
`zones` key fails when `zones` is undefined.

### Pitfall 6: Missed `global_mode` references in `async_evaluate`

**What goes wrong:** `coordinator.py` lines 216–222 read
`config["global_mode"]` directly to compute `_last_active_period` and fire the
status. After DEFAULT_CONFIG no longer has this key, an unmigrated storage file
(loaded through the compat shim correctly) will have `default_zone["mode"]`
instead. The compat shim promotes the key correctly at load time, but
`async_evaluate` will fail with `KeyError: 'global_mode'`.

**How to avoid:** Change lines 216–222 in coordinator.py:
```python
# Before:
global_mode = config["global_mode"]
self._last_active_period = (
    evaluate_schedule(config["global_time_program"], now)
    if global_mode != MODE_OFF
    else None
)

# After (D-05):
# _last_active_period still useful as room fallback, but reads from default_zone
dz = config["default_zone"]
self._last_active_period = (
    evaluate_schedule(dz["time_program"], now)
    if dz["mode"] != MODE_OFF
    else None
)
```

---

## Code Examples

### Storage compat shim (D-02/D-03)

```python
# Source: 14-CONTEXT.md D-02/D-03 + existing storage.py patterns
# In storage.py async_load(), after GAP-01 migration block, before return:

if "global_mode" in result and "default_zone" not in result:
    # Legacy format — build default_zone from flat keys.
    # Day-fill pass on global_time_program before absorbing it.
    tp = result.get("global_time_program", {})
    for day, periods in tp.items():
        if not periods:
            tp[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])
    result["default_zone"] = {
        "name": result.pop("default_zone_name", "Home"),
        "mode": result.pop("global_mode"),
        "time_program": result.pop(
            "global_time_program",
            copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
        ),
        "preheat_enabled": result.pop(
            "default_zone_preheat_enabled", False
        ),
    }
else:
    # New format — day-fill pass on default_zone["time_program"].
    tp = result.get("default_zone", {}).get("time_program", {})
    for day, periods in tp.items():
        if not periods:
            tp[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])

return result
```

### Frontend StatusPayload fallback (D-13/D-15)

```typescript
// Source: 14-CONTEXT.md D-13/D-15
// In any component reading the default zone's mode from status:
const defaultZoneMode =
  this.status?.zones?.["default"]?.mode
  ?? this.config?.default_zone?.mode
  ?? "";

// Replacing: this.status?.global_mode ?? this.config?.global_mode ?? ""
```

### Frontend ClimateConfig migration (D-12)

```typescript
// Source: 14-CONTEXT.md D-12
// types.ts — replace 4 flat properties with one:

// REMOVE:
//   global_mode: string;
//   global_time_program: DailyProgram;
//   default_zone_name: string;
//   default_zone_preheat_enabled?: boolean;

// ADD:
default_zone: ZoneConfig;
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Default Zone as 4 flat config keys | Default Zone as `default_zone: ZoneConfig` nested under single key | Phase 14 | `_resolve_zone_config` becomes uniform; no special-casing |
| `set_global_mode` WS command | `set_zone_mode(zone_id="default", mode=...)` | Phase 14 | Reduces WS command surface by 2 |
| `reset_time_program` WS command | `reset_zone_time_program(zone_id="default", target="default")` | Phase 14 | Unified reset contract for all zones |
| `reset_room_to_global_program` WS command | `reset_room_to_default_zone_program` | Phase 14 | Command name reflects actual semantics |

**Deprecated/outdated after this phase:**
- `config.global_mode` (frontend): replaced by `config.default_zone.mode`
- `config.global_time_program` (frontend): replaced by `config.default_zone.time_program`
- `config.default_zone_name` (frontend): replaced by `config.default_zone.name`
- `config.default_zone_preheat_enabled` (frontend): replaced by `config.default_zone.preheat_enabled`
- `status.global_mode` (frontend): replaced by `status.zones["default"].mode`
- `status.active_period` (frontend top-level): replaced by `status.zones["default"].active_period`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_last_active_period` remains useful as a room fallback in `_build_status_payload` room loop (line 1514 uses it as fallback for `_last_room_periods`). | Architecture Patterns / Pitfall 2 | If removed, rooms without a per-room period entry show `null` instead of the zone period. Low risk — behavior already verified in existing tests. |
| A2 | The `_build_status_payload` sensor-read code in `ws_get_status` (lines 195–258) is identical to the sensor-read code in `coordinator._build_status_payload` (lines 1542–1578). D-07 merges them by delegating ws_get_status to `_build_status_payload`. | Architecture Patterns (Pattern 5) | If there are undocumented differences, the delegation could change visible behavior for `get_status` callers (vs. `subscribe_status` push). Must verify by code inspection before deleting ws_get_status sensor block. |

---

## Open Questions

1. **`has_trv` field in ws_get_status but absent from `_build_status_payload`**
   - What we know: `ws_get_status` room_entry includes `has_trv` (line 243);
     `_build_status_payload` room_entry also includes `has_trv` (line 1578).
     Both call `is_trv_entity`. They appear identical.
   - What's unclear: whether Phase 14 D-07 delegation removes `has_trv` from
     `ws_get_status`'s code path if the delegation is a full replacement.
   - Recommendation: inspect both implementations for any field present in one
     but not the other before finalising the delegation. The plan task for D-07
     should include a diff step.

2. **Coordinator `_last_active_period` cleanup scope**
   - What we know: `_last_active_period` is set in `async_evaluate` (line 218)
     and read in `ws_get_status` (line 169) and in `_build_status_payload`
     (line 1514 as fallback). After D-07, `ws_get_status` delegates entirely
     to `_build_status_payload`, so the `getattr(coordinator,
     "_last_active_period", None)` read in ws_get_status is deleted.
   - What's unclear: whether `_last_active_period` as an instance variable
     should be formally removed or left as a private field (used only
     internally as room fallback).
   - Recommendation: retain `_last_active_period` as an instance variable
     (remove the `ws_get_status` read; keep the `_build_status_payload`
     fallback use). Clean removal can be a Phase 15 housekeeping task.

---

## Environment Availability

Step 2.6: SKIPPED — phase is purely code/config changes; no new external
dependencies, tools, or services are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-homeassistant-custom-component |
| Config file | `pytest.ini` / `pyproject.toml` (project root) |
| Quick run command | `make test` (runs `.venv/bin/python -m pytest tests/ -v`) |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 (storage) | Old format loads with `default_zone` synthesised | unit | `make test` → `test_storage.py` | ✅ (needs new tests) |
| ARCH-01 (storage) | New format loads correctly from `default_zone` key | unit | `make test` → `test_storage.py` | ❌ Wave 0 |
| ARCH-01 (coordinator) | `_resolve_zone_config` reads from `default_zone` | unit | `make test` → `test_coordinator.py` | ❌ Wave 0 (existing tests need update) |
| ARCH-01 (websocket) | `set_zone_mode("default", ...)` sets `default_zone.mode` | unit | `make test` → `test_websocket.py` | ❌ Wave 0 |
| ARCH-01 (websocket) | `set_global_mode` command removed (returns error) | unit | `make test` → `test_websocket.py` | ❌ Wave 0 |
| ARCH-01 (websocket) | `reset_room_to_default_zone_program` replaces old command | unit | `make test` → `test_websocket.py` | ❌ Wave 0 |
| ARCH-01 (status) | `get_status` response has `zones.default.mode` not `global_mode` | unit | `make test` → `test_websocket.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_storage.py` — add compat shim tests (old format → default_zone,
  new format → direct read, day-fill in both paths)
- [ ] `tests/test_coordinator.py` — update `_make_runtime_config` helper to
  use `default_zone` shape; update all 40+ usages; add `_last_zone_periods`
  tests
- [ ] `tests/test_websocket.py` — add `set_zone_mode("default", ...)` tests;
  update `set_global_mode` test to expect ERR_NOT_FOUND or command removal;
  update `reset_room_to_global_program` test name + assertions

*(Existing test infrastructure (pytest, conftest.py, hass fixture) covers all
phase requirements — only test content needs updating, not infrastructure.)*

---

## Security Domain

This phase contains no authentication, session management, or cryptographic
operations. Applicable ASVS categories:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | HA WebSocket auth gate (unchanged) |
| V5 Input Validation | yes | `vol.In(VALID_MODES)` extended to `zone_id="default"` path |
| V6 Cryptography | no | — |

**Relevant threat pattern:** The `set_zone_mode` handler must validate
`zone_id="default"` before zones dict lookup (T-05-01 pattern — already
established). The `vol.In(VALID_MODES)` schema gate already rejects invalid
modes regardless of zone_id. No new ASVS controls are needed beyond applying
the existing T-05-01 sentinel-first pattern to the extended handlers.

---

## Project Constraints (from CLAUDE.md)

- **Line endings:** LF on all files
- **Final newline:** every file must end with a newline
- **Trailing whitespace:** never
- **Python:** 4-space indent, max 80 characters per line
- **TypeScript/JavaScript:** 2-space indent, max 80 characters per line
- **JSON/YAML:** 2-space indent
- **Markdown:** 2-space indent, max 80 characters per line
- **Run `make lint` before committing** to validate editorconfig
- **GSD workflow enforcement:** all edits through `/gsd-execute-phase`
- **`make build && make deploy`** after any frontend change
- **No new PyPI dependencies** (v1 constraint, HACS compatibility)

---

## Sources

### Primary (HIGH confidence — direct code inspection)

- `custom_components/climate_manager/const.py` — full file read; confirmed
  `DEFAULT_CONFIG` shape with 4 flat keys
- `custom_components/climate_manager/storage.py` — full file read; confirmed
  compat shim insertion point and existing migration patterns
- `custom_components/climate_manager/coordinator.py` lines 100–250, 1315–1590
  — confirmed `_resolve_zone_config`, `async_evaluate`, `_build_status_payload`
  exact current code
- `custom_components/climate_manager/websocket.py` lines 1–140, 329–356,
  665–730, 840–895, 1086–1141 — confirmed all handlers to change
- `frontend/src/types.ts` — full file; confirmed `ClimateConfig`,
  `StatusPayload`, `ZoneConfig` interfaces
- `frontend/src/main.ts` lines 490–550 — confirmed synthesis block location
  (lines 509–512)
- `frontend/src/ws-client.ts` — full file; confirmed `setGlobalMode` (line 39),
  `resetRoomToGlobalProgram` (line 174) targets
- `frontend/src/components/global-settings-tab.ts` lines 540–563 — confirmed
  flat key reads at lines 546–547
- `frontend/src/components/room-card.ts` lines 405–525 — confirmed
  `global_mode` / `default_zone_name` reads
- `frontend/src/components/zone-tab.ts` lines 260–295, 570–605 — confirmed
  `default_zone_name` reads
- `tests/test_storage.py` — full file; identified 5 tests needing updates
- `tests/test_coordinator.py` lines 80–110 — identified `_make_runtime_config`
  helper using old flat keys

### Secondary (MEDIUM confidence)

- `14-CONTEXT.md` decisions D-01 through D-16 — authoritative user decisions
  from discuss-phase; implementation patterns derived from these

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing stack confirmed by code
- Architecture: HIGH — all patterns derived from direct codebase inspection and
  locked CONTEXT.md decisions
- Pitfalls: HIGH — all pitfalls identified from concrete code lines inspected

**Research date:** 2026-06-03
**Valid until:** 2026-07-03 (stable codebase; 30-day window)

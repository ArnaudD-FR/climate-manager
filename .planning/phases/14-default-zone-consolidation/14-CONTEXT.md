# Phase 14: Default Zone Consolidation - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Consolidate the Default Zone from 4 scattered flat config keys
(`global_mode`, `global_time_program`, `default_zone_name`,
`default_zone_preheat_enabled`) into a single `default_zone: ZoneConfig`
key in `DEFAULT_CONFIG` and `runtime_config`.

**In scope:**

- `DEFAULT_CONFIG` and `runtime_config`: replace 4 flat keys with
  `default_zone: ZoneConfig` (name, mode, time_program, preheat_enabled)
- `coordinator.py`: `_resolve_zone_config` reads from
  `config["default_zone"]` with no special-casing; adds `_last_zone_periods`
  dict for per-zone active period tracking; `_build_status_payload` updated
- `websocket.py`: remove `set_global_mode` and `reset_time_program`;
  extend `set_zone_mode` and `reset_zone_time_program` to accept
  `zone_id="default"`; rename `reset_room_to_global_program` →
  `reset_room_to_default_zone_program`; update `zone_id="default"` sentinel
  paths in `set_zone_preheat` and `rename_zone` to write `default_zone.*`
  keys; `ws_get_status` delegates to `coordinator._build_status_payload()`
- `storage.py`: lazy read-time compat shim builds `default_zone` in memory
  from flat keys on load (no write-back); existing day-fill logic moves
  inside the shim
- `StatusPayload` redesign: remove `global_mode` + top-level
  `active_period`; add `zones: Record<string, { mode, active_period }>`
- Frontend types + components: full migration (types.ts, main.ts, zone-tab,
  room-card, global-settings-tab, ws-client)

**Out of scope:**

- `room_mode: custom` removal — Phase 15
- Per-zone boiler declaration, demand control — deferred
- Multi-language labels
- Phase 15+ observability / logging

</domain>

<decisions>
## Implementation Decisions

### Config Schema

- **D-01:** `DEFAULT_CONFIG` replaces 4 flat keys with a single
  `default_zone` key shaped as a full `ZoneConfig`:
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

### Storage Migration

- **D-02:** Lazy read-time compat shim in `storage.py`. On every load,
  if old format is detected (`global_mode` present, `default_zone` absent),
  build `default_zone` in memory from the flat keys. No explicit write-back
  — old configs stay in storage until the first mutation triggers a normal
  `async_save()`, which persists the new format.
- **D-03:** The existing `global_time_program` day-fill logic (post-merge
  fill for missing day keys) moves inside the compat shim and applies to
  `default_zone["time_program"]` in both the legacy and new-format paths.
  Single unified load-time normalization step.

### Coordinator

- **D-04:** `_resolve_zone_config` removes the Default Zone special-case
  (`if zone_id is None: return config["global_mode"], config["global_time_program"]`).
  Default Zone rooms have no `zone_id` — they resolve to
  `config["default_zone"]["mode"]` and `config["default_zone"]["time_program"]`
  via the same code path as custom zones.
- **D-05:** Coordinator adds `_last_zone_periods: dict[str, str | None]`
  instance variable. During `async_evaluate`, the active period for each
  zone (Default Zone = `"default"`, custom zones by UUID) is written into
  this dict. Used by `_build_status_payload` to populate
  `zones[id].active_period`.
- **D-06:** `_build_status_payload` removes `global_mode` and top-level
  `active_period` from the returned dict. Adds:
  ```python
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
  }
  ```
- **D-07:** `ws_get_status` is refactored to call
  `coordinator._build_status_payload()` directly for the
  `zones`/`present_persons`/`rooms_status` fields, eliminating the
  existing duplication. Sensor reads (temperature/humidity) remain in
  `_build_status_payload`.

### WebSocket Commands

- **D-08:** `set_global_mode` command is **removed**. `set_zone_mode` is
  extended to accept `zone_id="default"`, writing to
  `runtime_config["default_zone"]["mode"]`. Frontend `ws-client.ts` removes
  `setGlobalMode()` and calls `setZoneMode("default", mode)` instead.
- **D-09:** `reset_time_program` command is **removed**. `reset_zone_time_program`
  is extended to handle `zone_id="default"` with `target="default"` (resets
  `default_zone.time_program` to `_DEFAULT_DAILY_PROGRAM`). Frontend calls
  `resetZoneTimeProgram("default", "default")`.
- **D-10:** `reset_room_to_global_program` is **renamed** to
  `reset_room_to_default_zone_program`. Internally reads from
  `runtime_config["default_zone"]["time_program"]` instead of
  `runtime_config["global_time_program"]`. Frontend `ws-client.ts` and any
  callers updated to use the new command name.
- **D-11:** `set_zone_preheat` and `rename_zone` already accept
  `zone_id="default"` via sentinel checks. Update their internal paths to
  read/write `runtime_config["default_zone"]["preheat_enabled"]` and
  `runtime_config["default_zone"]["name"]` respectively.

### Frontend — Config Shape

- **D-12:** `types.ts` `ClimateManagerConfig` interface: remove
  `global_mode`, `global_time_program`, `default_zone_name`,
  `default_zone_preheat_enabled`. Add `default_zone: ZoneConfig`. The
  `ZoneConfig` interface already exists (used for custom zones).
- **D-13:** `StatusPayload` interface: remove `global_mode` and
  `active_period`. Add:
  ```typescript
  zones: Record<string, { mode: string; active_period: string | null }>;
  ```
- **D-14:** `main.ts` removes the inline synthesis block (lines 509–512)
  that constructs a ZoneConfig from flat keys. Passes `config.default_zone`
  directly to zone-tab as the Default Zone's config object.
- **D-15:** Component read-path updates:
  - `global-settings-tab.ts`: `this.config.default_zone_name` →
    `this.config.default_zone.name`; `this.status?.global_mode` →
    `this.status?.zones?.["default"]?.mode`; `this.status?.active_period` →
    `this.status?.zones?.["default"]?.active_period`
  - `room-card.ts`: `this.panelConfig?.global_mode` →
    `this.panelConfig?.default_zone?.mode`; `this.status?.global_mode` →
    `this.status?.zones?.["default"]?.mode`;
    `this.panelConfig?.default_zone_name` →
    `this.panelConfig?.default_zone?.name`; similar for `global_time_program`
  - `zone-tab.ts`: `this.config.default_zone_name` →
    `this.config.default_zone.name`; `this.config.global_time_program` →
    `this.config.default_zone.time_program`
- **D-16:** `ws-client.ts`: add `setZoneMode("default", mode)` call;
  remove `setGlobalMode()`; update `resetRoomToGlobalProgram()` →
  `resetRoomToDefaultZoneProgram()`; add `resetZoneTimeProgram("default",
  "default")` path.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` §Architecture Cleanup — ARCH-01 defines
  acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 14 — phase boundaries and success criteria

### Key Source Files — Backend

- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG`,
  `DEFAULT_GLOBAL_MODE`, `_DEFAULT_DAILY_PROGRAM`, existing `ZoneConfig`
  shape (look at `zones` entries) — read fully before modifying DEFAULT_CONFIG
- `custom_components/climate_manager/coordinator.py` —
  `_resolve_zone_config()` (lines 1315–1334), `async_evaluate()` zone loop
  (line 366+), `_build_status_payload()` (line 1494), `_last_active_period`
  / `_last_room_periods` / `_last_zone_periods` (to add) — read fully before
  touching coordinator
- `custom_components/climate_manager/storage.py` — `_merge_with_defaults()`
  / post-merge fill logic (lines 93–169) — the compat shim lives here
- `custom_components/climate_manager/websocket.py` — `_make_ws_set_global_mode`
  (line 329), `_make_ws_set_zone_mode` (line 850), `_make_ws_set_zone_preheat`
  (line 900), `_make_ws_rename_zone`, `_make_ws_reset_zone_time_program`
  (line 1093), `_make_ws_reset_room_to_global_program` — read all before
  any command changes

### Key Source Files — Frontend

- `frontend/src/types.ts` — `ClimateManagerConfig` (line 106+),
  `StatusPayload` (line 177), `ZoneConfig` (line 93) — the migration
  starts here
- `frontend/src/main.ts` — Default Zone synthesis block (lines 509–512),
  `_subscribeStatus` (line 250), `_status` property usage — read before
  touching config passing
- `frontend/src/components/global-settings-tab.ts` — lines 546–548
  (zone config construction from flat keys)
- `frontend/src/components/room-card.ts` — lines 416, 420, 459, 505
  (global_mode, default_zone_name reads)
- `frontend/src/components/zone-tab.ts` — line 268, 585
  (default_zone_name, global_time_program reads)
- `frontend/src/ws-client.ts` — `setGlobalMode()` (line 41),
  `resetRoomToGlobalProgram()` (line 173) — commands to rename/remove

### Established Patterns

- Phase 5 CONTEXT.md — ZoneConfig storage shape and `zones` dict pattern;
  `zone_id="default"` sentinel convention already in use
- Phase 6 CONTEXT.md — zone tab frontend patterns, zone-tab component
  interface

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `coordinator.py:_resolve_zone_config` — current special-case (lines
  1315–1334) shows exactly what to remove; Default Zone fallback reads
  `config["global_mode"]` / `config["global_time_program"]` — replace with
  `config["default_zone"]["mode"]` / `config["default_zone"]["time_program"]`
- `coordinator.py:_build_status_payload` — full implementation at line 1494;
  `ws_get_status` (line 154) duplicates it — the refactor makes ws_get_status
  call `_build_status_payload()` and removes the duplicate sensor-read block
- `storage.py:_merge_with_defaults` — existing day-fill pass (lines 93–124)
  is the insertion point for the compat shim; follow the same guard pattern
  (`result.get("key")`) for old-format detection
- `types.ts:ZoneConfig` (line 93) — already has `mode`, `time_program`,
  `preheat_enabled`; only `name` needs to be added to the interface (or
  confirmed present) for Default Zone use

### Established Patterns

- **`zone_id="default"` sentinel:** already used in `set_zone_preheat` and
  `rename_zone` — follow the same branching style for `set_zone_mode` and
  `reset_zone_time_program`
- **Sparse config dict:** absent key = Default Zone; `zones` dict only
  contains custom zones — Default Zone lives separately under `default_zone`
- **`copy.deepcopy` for time programs:** always deepcopy when seeding or
  resetting time programs (established in Phase 7 for even/odd schedules)
- **`vol.In(VALID_MODES)` validation:** already in `set_zone_mode` schema —
  reuse for the `zone_id="default"` path

### Integration Points

- `coordinator.py:async_evaluate` area loop (line 183+) — add per-zone
  active period recording to `_last_zone_periods` inside the zone sweep
- `storage.py:_merge_with_defaults` return path — insert compat shim before
  returning merged result
- `websocket.py:setup_websocket_api` (line 94+) — remove registration of
  `set_global_mode` and `reset_time_program`; ensure `set_zone_mode` and
  `reset_zone_time_program` are still registered

</code_context>

<specifics>
## Specific Ideas

- The lazy compat shim in storage.py should detect old format via
  `"global_mode" in result and "default_zone" not in result` — explicit
  guard that won't false-positive on new-format configs that happen to have
  a `global_mode` key from another source.
- `_last_zone_periods` key for the Default Zone: use the string `"default"`
  (matches the `zone_id="default"` sentinel convention already throughout
  the codebase), not a UUID.
- `ws_get_status` refactor: after delegating `zones`/`present_persons`/
  `rooms_status` to `_build_status_payload()`, the handler becomes a thin
  wrapper: call `coordinator._build_status_payload()` and send the result.
  The current ws_get_status sensor-read duplication is eliminated entirely.
- Frontend: `status?.zones?.["default"]?.mode` — use optional chaining
  throughout since `zones` may be absent during initial load before first
  push. Fall back to `config.default_zone.mode` (same `??` pattern as
  current `status?.global_mode ?? config.global_mode`).

</specifics>

<deferred>
## Deferred Ideas

- **`room_mode: custom` removal** — Phase 15 (ARCH-02). Not touched here.
- **Per-zone boiler declaration** — deferred (v1.4+).
- **Full `get_status` → `get_zone_status` rename** — the command name stays
  as `get_status` for now; the payload shape changes but the command type
  string is unchanged to avoid unnecessary WS API churn.

### Reviewed Todos (not folded)

- "Add multi-language support" — false-positive match; deferred to a
  post-v1.3 effort, out of scope for Phase 14.
- "Per-zone boiler declaration with shared boiler support" — out of scope;
  deferred to v1.4+.
- "Boiler demand control" — out of scope; deferred to v2.

</deferred>

---

*Phase: 14-default-zone-consolidation*
*Context gathered: 2026-06-03*

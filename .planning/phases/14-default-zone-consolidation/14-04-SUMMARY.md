---
phase: 14-default-zone-consolidation
plan: "04"
subsystem: frontend
tags:
  - schema-migration
  - frontend
  - default-zone
  - typescript
dependency_graph:
  requires:
    - set_global_mode removed; set_zone_mode handles zone_id="default" (D-08,
      plan 03)
    - reset_time_program removed; reset_zone_time_program handles
      zone_id="default" (D-09, plan 03)
    - reset_room_to_default_zone_program command available (D-10, plan 03)
    - _build_status_payload emits zones dict (D-06, plan 02)
  provides:
    - ClimateConfig.default_zone: ZoneConfig (D-12)
    - StatusPayload.zones: Record<string, {mode, active_period}> (D-13)
    - main.ts passes config.default_zone directly to zone-tab (D-14)
    - All component read-paths use default_zone / status.zones["default"] (D-15)
    - ws-client exposes resetRoomToDefaultZoneProgram; setGlobalMode and
      resetTimeProgram removed (D-08/D-09/D-10/D-16)
    - panel.js rebuilt and deployed
  affects:
    - frontend/src/types.ts
    - frontend/src/main.ts
    - frontend/src/ws-client.ts
    - frontend/src/components/global-settings-tab.ts
    - frontend/src/components/room-card.ts
    - frontend/src/components/zone-tab.ts
    - custom_components/climate_manager/www/panel.js (built, not in git)
tech_stack:
  added: []
  patterns:
    - "mandatory three-level optional chaining
      status?.zones?.['default']?.mode ?? config.default_zone.mode (Pitfall 5)"
    - "direct config.default_zone passthrough in main.ts (D-14)"
    - "unified setZoneMode for both default and custom zones (D-08)"
key_files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/main.ts
    - frontend/src/ws-client.ts
    - frontend/src/components/global-settings-tab.ts
    - frontend/src/components/room-card.ts
    - frontend/src/components/zone-tab.ts
decisions:
  - "D-12/D-13: ClimateConfig.default_zone and StatusPayload.zones are the
    sole interface surface; all four flat keys and global_mode/active_period
    removed"
  - "D-14: main.ts passes config.default_zone directly — no in-template
    synthesis"
  - "D-15: mandatory three-level optional chaining guards against absent zones
    dict during initial load before first status push"
  - "D-16: ws-client drops setGlobalMode/resetTimeProgram and exposes
    resetRoomToDefaultZoneProgram"
  - "zone-tab._onModeChange unified: setZoneMode(this.zoneId, mode) works for
    both default and custom zones; isDefault branch removed"
  - "room-card seeding Custom program from default_zone.time_program (was
    global_time_program)"
metrics:
  duration_minutes: 15
  completed: "2026-06-04T17:25:33Z"
  tasks_completed: 2
  files_changed: 6
---

# Phase 14 Plan 04: Frontend Default Zone Migration Summary

Migrated the frontend TypeScript types, main panel, WebSocket client, and all
three components to the consolidated Default Zone shape — ClimateConfig now
exposes `default_zone: ZoneConfig` and StatusPayload now exposes
`zones: Record<string, { mode, active_period }>` instead of flat
`global_mode`/`active_period` keys. Panel rebuilt and deployed.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migrate types, main.ts, ws-client to default_zone shape | 42610d2 | types.ts, main.ts, ws-client.ts |
| 2 | Migrate component read-paths + rebuild and deploy panel | b2ab108 | global-settings-tab.ts, room-card.ts, zone-tab.ts |

## Task 3: CHECKPOINT PENDING

Task 3 is a `checkpoint:human-verify` gate requiring human verification that
the Default Zone renders and mutates correctly in the panel after the migration.
It was not executed by this agent.

**How to verify:**
1. Restart Home Assistant (or reload the Climate Manager integration) so
   the new panel.js and backend load together.
2. Open the Climate Manager panel sidebar.
3. Global settings / zone tab: confirm the Default Zone shows its name
   ("Home" unless renamed) and its current mode badge.
4. Change the Default Zone mode; confirm it persists after a page refresh
   (this exercises set_zone_mode("default", ...)).
5. Open a room card on the Default Zone: confirm the mode badge and active
   period render (no blank/undefined), and that the zone name shows.
6. Use the zone-tab "Reset to Home" action; confirm the toast shows the
   Default Zone name and the time program resets.
7. Confirm no console errors (especially no "Cannot read properties of
   undefined" from optional-chaining) during initial load before the first
   status push.

## What Was Built

### Task 1 — types.ts, main.ts, ws-client.ts

- `types.ts`: Removed `global_mode`, `global_time_program`,
  `default_zone_name`, `default_zone_preheat_enabled` from `ClimateConfig`.
  Added `default_zone: ZoneConfig` (D-12). Removed `global_mode` and
  `active_period` from `StatusPayload`. Added
  `zones: Record<string, { mode: string; active_period: string | null }>`
  (D-13).

- `main.ts`: Replaced the four-flat-key synthesis block with direct
  `.zoneConfig=${this._config!.default_zone}` passthrough (D-14). Updated
  the zone tab label and double-click rename handler to use
  `default_zone.name`.

- `ws-client.ts`: Removed `setGlobalMode()` (D-08). Removed
  `resetTimeProgram()` (D-09). Renamed `resetRoomToGlobalProgram()` to
  `resetRoomToDefaultZoneProgram()` with updated command type string
  `climate_manager/reset_room_to_default_zone_program` (D-10).

### Task 2 — Components + panel build

- `global-settings-tab.ts`: Default Zone row in `_getZoneRows()` now reads
  `this.config.default_zone.name`, mode via
  `this.status?.zones?.["default"]?.mode ?? this.config.default_zone.mode`,
  and active period via `this.status?.zones?.["default"]?.active_period`
  (mandatory three-level chaining, Pitfall 5 / T-14-08).

- `room-card.ts`: `_getZoneName()` returns
  `panelConfig?.default_zone?.name ?? "Default Zone"`. `_renderPeriodBadge()`
  and `_renderHeaderStatus()` read
  `status?.zones?.["default"]?.mode ?? panelConfig?.default_zone?.mode ?? ""`.
  Custom program seeding updated to use `default_zone.time_program`.
  `_onResetToGlobal()` calls `resetRoomToDefaultZoneProgram()`. Zone
  select option label uses `panelConfig?.default_zone?.name`.

- `zone-tab.ts`: `_onModeChange()` now calls `setZoneMode(this.zoneId, mode)`
  for both Default Zone and custom zones (unified path, no isDefault
  branch). `_onResetToGlobal()` toast and reset button label use
  `config.default_zone.name`.

- `make lint` and `make build` both exit 0. `make deploy` deployed the
  rebuilt panel.js to Home Assistant.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] main.ts tab label and rename handler still used
   default_zone_name flat key**

- **Found during:** Task 1 verification
- **Issue:** The plan described the synthesis block replacement in
  `_renderTabContent` but the tab button (line 440) and its label (line 457)
  also read `this._config!.default_zone_name`. Without fixing these, the
  TypeScript compiler would fail during `make build`.
- **Fix:** Updated both occurrences to `this._config!.default_zone.name`.
- **Files modified:** `frontend/src/main.ts`
- **Commit:** 42610d2

**2. [Rule 2 - Missing] zone-tab._onModeChange used setGlobalMode for Default
   Zone**

- **Found during:** Task 2 verification (grep scan)
- **Issue:** `zone-tab.ts` line 239 called `this.ws.setGlobalMode(newMode)`
  when `isDefault` was true. After removing `setGlobalMode()` from ws-client,
  this would cause a runtime TypeError. The plan mentioned only callers in
  global-settings-tab and zone-tab but did not specify the exact line in
  `_onModeChange`. The backend `set_zone_mode("default", ...)` already handles
  this — the isDefault branch is unnecessary.
- **Fix:** Removed the `if (this.isDefault)` branch; all mode changes now go
  through `setZoneMode(this.zoneId, newMode)` which accepts `"default"`.
- **Files modified:** `frontend/src/components/zone-tab.ts`
- **Commit:** b2ab108

**3. [Rule 1 - Bug] room-card seeded Custom program from global_time_program
   flat key**

- **Found during:** Task 2 verification (grep scan)
- **Issue:** `room-card.ts` line 349 read
  `this.panelConfig.global_time_program` to seed a room's Custom time program
  when the user first switches to Custom mode. This flat key no longer exists.
- **Fix:** Updated to `this.panelConfig.default_zone.time_program` (same
  semantic intent — seed from the Default Zone program).
- **Files modified:** `frontend/src/components/room-card.ts`
- **Commit:** b2ab108

**4. [Rule 1 - Bug] room-card called resetRoomToGlobalProgram**

- **Found during:** Task 2 verification (grep scan)
- **Issue:** `room-card.ts:_onResetToGlobal` called
  `this.ws.resetRoomToGlobalProgram(this.roomId)` which was renamed in
  ws-client.ts (Task 1).
- **Fix:** Updated to `this.ws.resetRoomToDefaultZoneProgram(this.roomId)`.
- **Files modified:** `frontend/src/components/room-card.ts`
- **Commit:** b2ab108

**5. [Rule 1 - Bug] room-card zone select option label used
   default_zone_name flat key**

- **Found during:** Task 2 verification (grep scan)
- **Issue:** `room-card.ts` line 1130 rendered
  `this.panelConfig?.default_zone_name ?? "Default Zone"` as the label for
  the Default Zone option in the zone assignment select.
- **Fix:** Updated to `this.panelConfig?.default_zone?.name ?? "Default Zone"`.
- **Files modified:** `frontend/src/components/room-card.ts`
- **Commit:** b2ab108

## Verification

- `grep -rEn '\.global_mode|\.global_time_program|\.default_zone_name|
  resetRoomToGlobalProgram|setGlobalMode' frontend/src/`: 0 matches
- `grep -c 'default_zone: ZoneConfig' frontend/src/types.ts`: 1
- `grep -c 'zones: Record<string, { mode: string; active_period'
  frontend/src/types.ts`: 1
- `grep -c 'resetRoomToDefaultZoneProgram' frontend/src/ws-client.ts`: 1
- main.ts line 508: `.zoneConfig=${this._config!.default_zone}` confirmed
- `make lint`: Passed
- `make build`: Exited 0 (panel.js 193 kB, gzip 42 kB)
- `make deploy`: Exited 0 (panel deployed to HA)

## Known Stubs

None — all read-paths wire to real config/status fields with proper fallbacks.

## Threat Flags

None — no new network endpoints or trust boundaries introduced. The three-level
optional chaining on `status?.zones?.["default"]?.mode` satisfies T-14-08
(pre-first-push render guard). The rebuilt panel.js satisfies T-14-09 (stale
bundle mitigated by make deploy).

## Self-Check: PASSED

- `frontend/src/types.ts`: `default_zone: ZoneConfig` present;
  `zones: Record<...>` in StatusPayload present; `global_mode`/
  `global_time_program`/`default_zone_name` absent from interface declarations
- `frontend/src/ws-client.ts`: `resetRoomToDefaultZoneProgram` present;
  `setGlobalMode` absent; `resetTimeProgram` absent
- `frontend/src/main.ts`: `.zoneConfig=${this._config!.default_zone}` present
  at line 508; `default_zone_name` absent from code
- `frontend/src/components/global-settings-tab.ts`: `this.config.default_zone.name`
  present; three-level chaining `zones?.["default"]?.mode` present
- `frontend/src/components/room-card.ts`: `default_zone?.name` present
  (3 occurrences); `zones?.["default"]?.mode` present (2 occurrences)
- `frontend/src/components/zone-tab.ts`: `default_zone.name` in toast and
  button; `setZoneMode` used for both default and custom zones
- Commits 42610d2 (Task 1) and b2ab108 (Task 2) verified in git log

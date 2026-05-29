---
phase: 06-zone-room-assignment-ui
plan: "01"
subsystem: frontend
tags: [websocket, lit, zone-management, ui]
dependency_graph:
  requires:
    - "05: zone CRUD WS commands (create_zone, delete_zone, rename_zone,
      set_zone_mode, set_zone_time_program, reset_zone_time_program)"
  provides:
    - "WsClient zone methods: createZone, deleteZone, renameZone, setZoneMode,
      setZoneTimeProgram, resetZoneTimeProgram"
    - "climate-manager-zone-tab custom element (zone editor UI)"
  affects:
    - "frontend/src/ws-client.ts — 6 new zone methods"
    - "frontend/src/components/zone-tab.ts — new file"
    - "custom_components/climate_manager/www/panel.js — Vite bundle updated"
tech_stack:
  added: []
  patterns:
    - "write-then-reload (await ws.X -> reloadConfig -> showToast)"
    - "memoized days getter (zoneConfig.time_program identity keyed)"
    - "click-to-edit name pattern (styled text -> input -> blur/Enter saves ->
      Escape cancels)"
    - "inline delete confirm row (no ha-dialog)"
    - "chip association with search-picker"
key_files:
  created:
    - frontend/src/components/zone-tab.ts
  modified:
    - frontend/src/ws-client.ts
    - custom_components/climate_manager/www/panel.js
decisions:
  - "createZone return type uses zone_id (not id) matching backend websocket.py
    payload at lines 545-553"
  - "zoneId='default' sentinel routes renameZone to backend default_zone_name
    (D-05/D-07)"
  - "_onRemoveRoom sends zone_id: undefined (sparse model) so absent key =
    Default Zone member (D-06)"
  - "Default Zone chip remove button hidden (rooms cannot be removed from
    Default Zone — no fallback zone)"
  - "HA 2026.x compatibility: native <input> and <select> only; no ha-textfield,
    ha-select, ha-tabs, paper-tab, ha-dialog"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-28"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 6 Plan 01: Zone WS Methods + Zone Tab Component Summary

WsClient gains 6 typed zone WebSocket methods and a new zone-tab.ts Lit
component (~590 lines) implementing the full per-zone editor (click-to-edit
name, native mode picker, time-bar with memoized days, assigned-rooms
chip+search-picker with inline delete confirm).

## Tasks Completed

| Task | Name                           | Commit  | Files                                                                               |
| ---- | ------------------------------ | ------- | ----------------------------------------------------------------------------------- |
| 1    | Add 6 zone methods to WsClient | 06319d3 | frontend/src/ws-client.ts                                                           |
| 2    | Create zone-tab.ts component   | 9e9e586 | frontend/src/components/zone-tab.ts, custom_components/climate_manager/www/panel.js |

## What Was Built

### Task 1: WsClient Zone Methods

Added 6 typed zone methods to `WsClient` in `frontend/src/ws-client.ts`, each
following the existing `sendMessagePromise` pattern:

1. `createZone(name: string)` — returns `{zone_id, name, mode, time_program}`
   matching backend payload
2. `deleteZone(zoneId: string)` — returns `{success: boolean}`
3. `renameZone(zoneId: string, name: string)` — supports `zoneId="default"`
   sentinel for Default Zone
4. `setZoneMode(zoneId: string, mode: string)` — same enum as global_mode
5. `setZoneTimeProgram(zoneId: string, program: DailyProgram)` — all 7 day keys
6. `resetZoneTimeProgram(zoneId: string, target: string)` — resets to named
   target

`ZoneConfig` added to the type import block.

### Task 2: ZoneTab Component

New `frontend/src/components/zone-tab.ts` (~590 lines) implementing the full
zone editor:

**Layout (D-04 top-to-bottom):**

1. Delete row (custom zones only): "Delete zone" button → click → inline "Delete
   zone? [Cancel] [Confirm]" row (D-05, no ha-dialog)
2. Zone name: click-to-edit (D-06/D-07); input replaces h2 on click, blur/Enter
   saves via `renameZone`, Escape cancels
3. Mode picker: native `<select>` with Off/Time program/Time program & presences
   options; auto-saves on change
4. Time-bar: `<climate-manager-time-bar>` fed by memoized `_days` getter
   (prevents drag flicker on status re-renders)
5. Assigned Rooms: chips with × remove button (hidden on Default Zone);
   `<search-picker>` for adding unassigned rooms

**Key design decisions:**

- `isDefault=true`: hides delete button (UI-05), hides chip remove buttons (no
  zone to send rooms to)
- `_getAssignedRoomIds()`: orphan-safe for Default Zone — absent zone_id OR
  zone_id not in config.zones
- `_onRemoveRoom()`: sends `{zone_id: undefined}` for sparse model (D-06
  phase 4)
- `_onAddRoom()`: sends `{zone_id: this.zoneId}` including `"default"` for
  Default Zone membership
- All 7+ write handlers use write-then-reload pattern

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing TypeScript errors in `frontend/src/components/time-bar.ts` (2
errors about `Period` discriminated union) were present before this plan and are
out of scope. They do not affect zone-tab.ts or ws-client.ts and did not prevent
the Vite build from succeeding.

## Known Stubs

None. `zone-tab.ts` is a fully functional component. All WS write methods are
wired to real backend commands. The component is ready to be imported by Plan 02
(main.ts dynamic zone tabs).

## Threat Surface Scan

No new threat surface beyond the plan's threat model:

- T-06-01 (Tampering: user-typed zone name): Mitigated — `_onNameBlur()` trims
  input client-side before sending to `renameZone`; backend validates
  non-empty + length (Phase 5).
- T-06-SC: No new package installs.
- Zone name rendered via Lit `html` template (auto-escaped, no innerHTML).

## Self-Check: PASSED

- frontend/src/ws-client.ts: FOUND
- frontend/src/components/zone-tab.ts: FOUND
- .planning/phases/06-zone-room-assignment-ui/06-01-SUMMARY.md: FOUND
- Commit 06319d3 (Task 1): FOUND
- Commit 9e9e586 (Task 2): FOUND

---
phase: 06-zone-room-assignment-ui
plan: 04
subsystem: backend-websocket, frontend-panel
tags: [gap-closure, zone-assignment, websocket, typescript, tdd]
dependency_graph:
  requires: [06-01, 06-02, 06-03]
  provides: [ASSIGN-01, ASSIGN-02, UI-01, UI-04, UI-06]
  affects:
    [
      custom_components/climate_manager/websocket.py,
      frontend/src/components/zone-tab.ts,
      frontend/src/components/room-card.ts,
      frontend/src/main.ts,
    ]
tech_stack:
  added: []
  patterns: [null-as-pop-signal, isDefault-branch-routing, tdd-red-green]
key_files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_storage.py
    - tests/test_websocket.py
    - frontend/src/components/zone-tab.ts
    - frontend/src/components/room-card.ts
    - frontend/src/main.ts
    - custom_components/climate_manager/www/panel.js
decisions:
  - "null-as-pop-signal: frontend sends zone_id: null to mean 'remove from
    zone'; backend handler pops the key per D-06 sparse model — TypeScript cast
    (null as unknown as string | undefined) kept local to two call sites,
    RoomConfig.zone_id type NOT widened"
  - "validator contract preserved: validate_zone_assignment still rejects stored
    null zone_id as defense in depth; the handler-side pop ensures the validator
    never sees null in the happy path"
metrics:
  duration: ~35 minutes
  completed: "2026-05-28T16:44:00Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 6 Plan 4: Gap Closure — Zone Mutation Wiring Summary

Six verified bugs from 06-VERIFICATION.md closed: backend null-pop for zone_id,
Default Zone mode/time-program routing to global endpoints, null payload for
room removal/add, and first tab label fix.

## What Was Built

Surgical fixes to six code-level wiring bugs that prevented Phase 6's zone
assignment UI from persisting any mutations to the backend. No architectural
changes — only exact-site repairs at the files/lines identified in the
verification report.

### Backend Fix (Task 1 — TDD)

**`custom_components/climate_manager/websocket.py` — `ws_set_room_config`:**

Added a null-check before the sparse-merge. When the frontend sends
`{zone_id: null}`, the handler:

1. Pops `zone_id` from `incoming_config` (so the merge doesn't write null)
2. Pops `zone_id` from the live room entry (moves room to Default Zone per D-06)
3. Proceeds with the existing sparse-merge, save, and evaluate flow

The `rooms_backup` CR-01 snapshot is taken before any mutation. The explanatory
comment "zone_id: null from the frontend signals 'move room to Default Zone'" is
present.

**`tests/test_storage.py`:** Added
`test_validate_zone_assignment_rejects_explicit_null` — locks the existing
defense-in-depth behavior (validator still rejects stored null).

**`tests/test_websocket.py`:** Added three handler behavior tests:

- `test_set_room_config_pops_zone_id_when_null` — zone_id key absent after null
- `test_set_room_config_null_zone_id_is_idempotent_when_already_absent` — no-op
  when key already missing
- `test_set_room_config_null_zone_id_preserves_other_keys` — targeted pop, other
  keys still applied

### Frontend Fixes (Task 2)

**`frontend/src/components/zone-tab.ts`:**

- `_onModeChange` (CR-01): Added `isDefault` branch — routes to
  `ws.setGlobalMode(newMode)` for Default Zone,
  `ws.setZoneMode(this.zoneId, newMode)` for custom zones
- `_onPeriodsChanged` (CR-02): Added `isDefault` branch — routes to
  `ws.setTimeProgram(program)` for Default Zone,
  `ws.setZoneTimeProgram(this.zoneId, program)` for custom zones; updated JSDoc
- `_onAddRoom` (WR-01): Added `isDefault` branch — sends `{zone_id: null}` for
  Default Zone, `{zone_id: this.zoneId}` for custom zones; updated comment
- `_onRemoveRoom` (CR-03): Changed `zone_id: undefined` to
  `zone_id: null as unknown as string | undefined` — JSON.stringify now
  preserves the key

**`frontend/src/components/room-card.ts`:**

- `_onZoneChange` (CR-03 mirror): Changed falsy-branch from `zone_id: undefined`
  to `zone_id: null as unknown as string | undefined`

**`frontend/src/main.ts`:**

- Line 288: First tab button label changed from `Overview` to `Global Settings`
  (UI-01)

## Test Results

- 121 tests pass (up from 117 — 4 new tests added)
- `npx vite build` succeeds (139.39 kB panel.js)
- `npx tsc --noEmit` has 2 pre-existing errors in `time-bar.ts` (not caused by
  this plan — present in baseline; Vite build unaffected)

## Deviations from Plan

### Pre-existing TypeScript Errors (out of scope)

`time-bar.ts` has 2 strict-mode TypeScript errors (Period union type mismatch)
that are present in the baseline before any changes in this plan. They are not
caused by our edits, do not affect the Vite build, and are logged here per
scope-boundary rules. Deferred to `deferred-items.md`.

None of the 6 task-specified edits deviated from the plan instructions.

## Threat Surface Scan

No new trust boundaries introduced. The `zone_id: null` interpretation adds a
semantic meaning to one existing WS field — not a new field or endpoint. The
STRIDE register in the plan (T-06-07, T-06-08, T-06-09) covers the surface: all
dispositions are `accept` with documented rationale.

## Self-Check

Files created/modified:

- custom_components/climate_manager/websocket.py: FOUND
- tests/test_storage.py: FOUND
- tests/test_websocket.py: FOUND
- frontend/src/components/zone-tab.ts: FOUND
- frontend/src/components/room-card.ts: FOUND
- frontend/src/main.ts: FOUND
- custom_components/climate_manager/www/panel.js: FOUND

Commits:

- 95fed28: test(06-04): add failing tests — FOUND
- db4104a: feat(06-04): ws_set_room_config pops zone_id — FOUND
- dc68615: feat(06-04): fix five frontend wiring bugs — FOUND
- 557c326: chore(06-04): rebuild panel.js — FOUND

## Self-Check: PASSED

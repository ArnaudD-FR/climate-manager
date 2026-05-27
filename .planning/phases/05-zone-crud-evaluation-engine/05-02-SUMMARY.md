---
phase: 05-zone-crud-evaluation-engine
plan: "02"
subsystem: websocket
tags: [websocket, zone-crud, tdd, validation, snapshot-rollback]
dependency_graph:
  requires: [05-01]
  provides: [delete_zone-ws, set_zone_time_program-ws, reset_zone_time_program-ws]
  affects: [websocket.py, tests/test_websocket.py]
tech_stack:
  added: []
  patterns:
    - CR-01 snapshot-rollback over zones+rooms in delete_zone
    - validate-before-mutate gate (Pitfall 6) in set_zone_time_program
    - copy.deepcopy for both target branches in reset_zone_time_program
key_files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
decisions:
  - delete_zone pops room zone_id keys BEFORE deleting the zone from zones dict (Pitfall 1 ordering)
  - CR-01 snapshot covers both zones AND rooms since delete_zone mutates both
  - validate_daily_program called before any runtime_config access in set_zone_time_program (Pitfall 6)
  - copy.deepcopy enforced for both 'default' and 'global' target branches (Pitfall 2)
metrics:
  duration: "~10min"
  completed: "2026-05-27T20:25:53Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 02: Zone Delete + Time Program WS Handlers Summary

**One-liner:** Three zone CRUD WebSocket handlers (delete, set_time_program, reset_time_program) with CR-01 snapshot-rollback, validate-before-mutate gate, and deepcopy isolation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add 5 failing tests for delete/set/reset time program | 4b25c77 | tests/test_websocket.py (+168 lines) |
| 2 (GREEN) | Implement 3 zone WS handler factories + 3 registrations | 7106c10 | custom_components/climate_manager/websocket.py (+168 lines) |

## What Was Built

Three new WebSocket command factories appended to `websocket.py` (zone CRUD section):

**`_make_ws_delete_zone`** (ZONE-07):
- Guards: `zone_id not in runtime_config["zones"]` → `ERR_NOT_FOUND`
- CR-01: snapshots both `zones` and `rooms` via `copy.deepcopy` before any mutation
- Pitfall 1 ordering: iterates rooms and calls `room_cfg.pop("zone_id", None)` BEFORE `del runtime_config["zones"][zone_id]`
- On `ValueError` from `store.async_save`: restores both snapshots, returns `ERR_INVALID_FORMAT`
- On success: `{success: True}` + schedule evaluate

**`_make_ws_set_zone_time_program`** (ZONE-09):
- Pitfall 6: `validate_daily_program(msg["program"])` called FIRST, before any `runtime_config` access
- Returns `ERR_INVALID_FORMAT` and exits immediately on invalid program (no mutation)
- Then guards for unknown zone_id, then assigns and saves

**`_make_ws_reset_zone_time_program`** (ZONE-09):
- Schema: `vol.In(["default", "global"])` restricts target values
- `target=="default"`: `copy.deepcopy(_DEFAULT_DAILY_PROGRAM)` (Pitfall 5 — never assign module constant directly)
- `target=="global"`: `copy.deepcopy(runtime_config["global_time_program"])` (Pitfall 2 — avoids shared list refs)

All three registered in `async_register_commands` (total: 17 commands).

## Verification Results

- `uv run pytest tests/test_websocket.py -x` → 19/19 passed
- `uv run pytest tests/ -x` → 117/117 passed (full suite)
- `grep -c '^    websocket_api.async_register_command' websocket.py` → 17

## Acceptance Criteria Check

- [x] websocket.py contains `def _make_ws_delete_zone(entry: ClimateManagerConfigEntry):`
- [x] websocket.py contains `def _make_ws_set_zone_time_program(entry: ClimateManagerConfigEntry):`
- [x] websocket.py contains `def _make_ws_reset_zone_time_program(entry: ClimateManagerConfigEntry):`
- [x] websocket.py contains `room_cfg.pop("zone_id", None)` inside _make_ws_delete_zone
- [x] `del runtime_config["zones"][zone_id]` follows after the rooms pop loop (line 673 pop, line 675 del)
- [x] websocket.py contains `validate_daily_program(msg["program"])` followed by `return` within 5 lines
- [x] websocket.py contains `vol.In(["default", "global"])` in reset_zone_time_program schema
- [x] websocket.py contains `copy.deepcopy(_DEFAULT_DAILY_PROGRAM)` AND `copy.deepcopy(runtime_config["global_time_program"])`
- [x] `grep -c '^    websocket_api.async_register_command'` returns 17
- [x] 5 new tests defined and all pass

## TDD Gate Compliance

- RED gate: commit `4b25c77` (`test(05-02): add 5 failing tests...`) — tests confirmed failing before implementation
- GREEN gate: commit `7106c10` (`feat(05-02): implement...`) — all 5 tests pass after implementation
- No REFACTOR phase needed (handlers are clean mechanical adaptations)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — all new surface (delete_zone, set_zone_time_program, reset_zone_time_program) was
anticipated in the plan's STRIDE threat register (T-05-06 through T-05-11); no new
unplanned network endpoints or auth paths introduced.

## Self-Check

### Files exist:
- custom_components/climate_manager/websocket.py — modified (contains all 3 factories)
- tests/test_websocket.py — modified (contains all 5 new tests)

### Commits exist:
- 4b25c77 — test(05-02) RED
- 7106c10 — feat(05-02) GREEN

## Self-Check: PASSED

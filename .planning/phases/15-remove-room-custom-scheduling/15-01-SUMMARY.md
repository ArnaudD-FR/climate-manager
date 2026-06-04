---
phase: 15-remove-room-custom-scheduling
plan: "01"
subsystem: backend-core
tags: [refactor, migration, room-mode-removal, storage-shim, tdd]
dependency_graph:
  requires: []
  provides:
    - "const.py: ROOM_MODE_* constants deleted"
    - "coordinator.py: zone-only temperature resolution"
    - "storage.py: Phase 15 compat shim stripping room_mode + time_program"
    - "tests/test_storage.py: Phase 15 shim test"
  affects:
    - "coordinator.py _compute_desired_temps"
    - "coordinator.py _apply_presence_overrides"
    - "coordinator.py _async_preheat_room"
    - "storage.py async_load"
tech_stack:
  added: []
  patterns:
    - "Pop-based compat shim in storage.py async_load (mirrors Phase 14 pattern)"
    - "Unconditional zone resolution via _resolve_zone_config"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/storage.py
    - tests/test_storage.py
    - tests/test_coordinator.py
    - tests/test_preheat.py
decisions:
  - "Lazy read-time compat shim in storage.py strips room_mode + time_program from rooms on every load (D-01/D-02/D-03)"
  - "Storage shim scoped to result.get('rooms', {}).values() — NOT result.values() — prevents stripping zone time_programs (Pitfall 2)"
  - "test_load_room_override_survives updated to test non-deprecated key survival instead of time_program survival"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-04"
  tasks_completed: 4
  files_modified: 6
---

# Phase 15 Plan 01: Remove room_mode from Python backend core Summary

Deleted ROOM_MODE_* constants, stripped all room_mode/ROOM_MODE branches from
coordinator and preheat logic, added lazy read-time storage compat shim, and
cleaned all room_mode references from coordinator and preheat tests. 250 tests
green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Wave 0 storage shim test (RED) | fcca36e | tests/test_storage.py |
| 2 | Delete ROOM_MODE_* constants from const.py | db9d10d | const.py |
| 3 | Strip room_mode branches from coordinator + add storage shim (GREEN) | cb048d3 | coordinator.py, storage.py, test_storage.py |
| 4 | Clean room_mode references from coordinator + preheat tests | f80db94 | test_coordinator.py, test_preheat.py |

## Verified Must-Haves

- **D-01:** After async_load(), no room record contains room_mode or time_program
- **D-02:** Storage shim is silent — no log emitted
- **D-03:** Zone time_program survives the shim untouched (scoped to rooms)
- **D-04:** Every room resolves via _resolve_zone_config; no ROOM_MODE_FROST or ROOM_MODE_CUSTOM branch
- **D-05:** Preheat logic has no room_config.get("room_mode") checks
- **D-14:** test_room_mode_* coordinator tests deleted; suite passes with no ROOM_MODE_* imports
- **D-15:** Incidental room_mode fixture data removed from surviving tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_load_room_override_survives tested deprecated behavior**

- **Found during:** Task 3 (storage shim added)
- **Issue:** The test stored a room `time_program` and asserted it survived
  `async_load()`. After Phase 15 shim, room `time_program` is stripped on load,
  causing the test to fail on a legitimate invariant change.
- **Fix:** Updated test to verify that non-deprecated keys (preheat_max_lead_minutes)
  survive load, correctly reflecting the new Phase 15 invariant.
- **Files modified:** tests/test_storage.py
- **Commit:** cb048d3

**2. [Rule 2 - D-15] Incidental room_mode fixture keys in test_storage.py**

- **Found during:** Task 3 (storage shim verification)
- **Issue:** PATTERNS.md identified lines 214, 233, 271 in test_storage.py as having
  incidental `room_mode` fixture data that needed removal per D-15.
- **Fix:** Removed `room_mode` from three fixture dicts in test_storage.py.
- **Files modified:** tests/test_storage.py
- **Commit:** cb048d3

## TDD Gate Compliance

- RED gate: fcca36e — `test(15-01): add failing Phase 15 shim test` (test FAILED before shim)
- GREEN gate: cb048d3 — `feat(15-01): strip room_mode branches + add storage shim` (all tests pass)

## Verification Results

```
grep -rc 'ROOM_MODE' const.py coordinator.py  → all 0
grep -c 'room_cfg.pop("room_mode", None)' storage.py  → 1
make test  → 250 passed
make lint  → all Passed
```

## Self-Check: PASSED

- [x] tests/test_storage.py contains `test_load_strips_room_mode_from_room_records`
- [x] custom_components/climate_manager/const.py: 0 ROOM_MODE occurrences
- [x] custom_components/climate_manager/coordinator.py: 0 ROOM_MODE/room_mode occurrences
- [x] custom_components/climate_manager/storage.py contains `room_cfg.pop("room_mode", None)`
- [x] storage.py shim iteration: `result.get("rooms", {}).values()`
- [x] tests/test_coordinator.py: 0 ROOM_MODE/room_mode occurrences
- [x] tests/test_preheat.py: 0 ROOM_MODE/room_mode occurrences
- [x] Commits fcca36e, db9d10d, cb048d3, f80db94 exist in git log
- [x] 250 tests pass
- [x] All linting passes

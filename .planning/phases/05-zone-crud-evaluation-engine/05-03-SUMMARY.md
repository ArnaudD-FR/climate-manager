---
plan: 05-03
phase: 05-zone-crud-evaluation-engine
status: complete
wave: 1
tasks_complete: 2/2
key-files:
  created: []
  modified:
    - custom_components/climate_manager/coordinator.py
    - tests/test_coordinator.py
requirements_covered:
  - EVAL-01
  - EVAL-02
  - EVAL-03
  - EVAL-04
  - EVAL-05
---

## Summary

Refactored coordinator from a top-level global_mode switch to a per-room zone-aware
dispatch loop. Added `_resolve_zone_config` helper. Removed `_evaluate_time_program`
and `_evaluate_time_program_presences`. Added 5 EVAL tests. All 43 tests green.

## Tasks

| Task | Status | Notes |
|------|--------|-------|
| Task 1 (RED tests) | ✓ | Extended _make_runtime_config + 5 EVAL tests; 3/5 failed against old coordinator |
| Task 2 (refactor GREEN) | ✓ | Coordinator refactored; all 5 EVAL tests now pass |

## What Was Built

- `_resolve_zone_config(area_id, config)`: returns `(mode, time_program)` for a room.
  Rooms without `zone_id` → Default Zone; dangling `zone_id` → warning + Default Zone fallback.
- `async_evaluate` unified loop: PASS 1 (room_mode short-circuit → zone resolution → baseline
  temp per room) + PASS 2 (presence override for `time_program_presences` zones only).
- `global_mode=off` now affects only Default Zone rooms (D-08/D-10); custom zone rooms
  follow their own zone's mode independently.
- `_last_active_period` still reflects Default Zone evaluated period (Pitfall 7 compat).

## Self-Check: PASSED

- `uv run pytest tests/test_coordinator.py tests/test_websocket.py -x` → 43 passed
- `grep 'if global_mode ==' coordinator.py` → 0 matches in async_evaluate body
- `_evaluate_time_program` and `_evaluate_time_program_presences` removed
- `_resolve_zone_config` present with correct signature
- EVAL-01..05 all green

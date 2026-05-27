---
phase: 04-zone-data-model-storage
plan: 01
subsystem: storage
tags: [python, storage, zones, schema, validation]

requires:
  - phase: 03-websocket-api-frontend-panel
    provides: ClimateManagerStore and DEFAULT_CONFIG baseline that this plan extends

provides:
  - DEFAULT_CONFIG with zones={} and default_zone_name="Home" (additive, STORAGE_VERSION=2 unchanged)
  - validate_zone_assignment() module-level helper in storage.py with ZONE-04 referential integrity
  - 9 new test functions covering ZONE-01..04 and v1.0 backward compat

affects:
  - 04-02-types (mirrors schema additions as TypeScript stubs)
  - phase 05 (zone CRUD — imports validate_zone_assignment from storage.py)
  - phase 06 (zone UI — reads zones/default_zone_name from get_config payload)

tech-stack:
  added: []
  patterns:
    - Additive DEFAULT_CONFIG extension — new keys alongside existing ones, STORAGE_VERSION unchanged
    - Module-level validator called from async_save before persistence
    - Sparse model — absent zone_id on room means Default Zone membership (no sentinel value)

key-files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/storage.py
    - tests/test_storage.py

key-decisions:
  - "D-01: Default Zone has no storage entry — absent zone_id means Default Zone (no sentinel ID)"
  - "D-02: Default Zone mode/schedule IS global_mode/global_time_program — no new fields"
  - "D-03: default_zone_name='Home' in DEFAULT_CONFIG; fresh install returns it; v1.0 data gets fallback"
  - "D-04: STORAGE_VERSION stays at 2 — all changes purely additive"
  - "D-05/D-06: zone_id on room (not room_ids on zone); absent = Default Zone membership"
  - "D-07: zone IDs are UUID strings — documented via import uuid in storage.py for Phase 5"

patterns-established:
  - "Validation helper: module-level function raises ValueError before _store.async_save — not in async_load (would reject v1.0 data)"
  - "Sparse merge safety: async_load unchanged so v1.0 data loads cleanly, new keys fill from DEFAULT_CONFIG"

requirements-completed:
  - ZONE-01
  - ZONE-02
  - ZONE-03
  - ZONE-04

duration: 35min
completed: 2026-05-27
---

# Phase 04-01: Zone Data Model — Python Backend Summary

**Extended DEFAULT_CONFIG with zone schema (zones={}, default_zone_name="Home"), added validate_zone_assignment() helper to storage.py, and grew test suite from 9 to 18 passing tests covering ZONE-01..04 and v1.0 backward compat — STORAGE_VERSION unchanged at 2**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-05-27
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- `DEFAULT_CONFIG` gains `zones: {}` and `default_zone_name: "Home"` with inline sub-schema comment block documenting the zone object shape and Default Zone virtual concept (D-01..D-07)
- `validate_zone_assignment(config)` module-level helper raises `ValueError` with "unknown zone_id" or "assigned to multiple rooms" messages; wired into `async_save` before `_store.async_save`; `async_load` left unchanged to avoid rejecting v1.0 data
- `import uuid` added to storage.py to document the D-07 UUID convention for Phase 5 consumers
- 9 new tests appended to `test_storage.py` — covers fresh install, v1.0 backward compat, round-trip, four direct helper tests, and two async save-path tests; all 18 pass

## Task Commits

1. **Task 1: Extend DEFAULT_CONFIG with zones schema (const.py)** — `a84a765` (feat)
2. **Task 2: Add validate_zone_assignment helper and wire into async_save (storage.py)** — `845149b` (feat)
3. **Task 3: Add zone-schema and ZONE-04 tests (tests/test_storage.py)** — `5792ed0` (test)

## Files Created/Modified
- `custom_components/climate_manager/const.py` — Added `zones: {}` and `default_zone_name: "Home"` to DEFAULT_CONFIG; new zones sub-schema comment block; zone_id documented in rooms sub-schema
- `custom_components/climate_manager/storage.py` — `import uuid` added; `validate_zone_assignment()` module-level function; `async_save` calls it before persistence
- `tests/test_storage.py` — 9 new test functions (109 lines); `validate_zone_assignment` import added

## Decisions Made
None beyond those locked in 04-CONTEXT.md (D-01 through D-07) — plan executed as specified.

## Deviations from Plan
None — plan executed exactly as written. The Bash permission issue in the agent caused the test commit to be handled by the orchestrator inline, but all code was written by the executor.

## Issues Encountered
- Bash permission was denied for the executor agent after writing the test file, preventing it from committing and running pytest. The orchestrator ran pytest (18/18 pass) and committed `tests/test_storage.py` directly.

## Next Phase Readiness
- `validate_zone_assignment` is importable from `storage.py` — ready for Phase 5 WebSocket handlers
- `DEFAULT_CONFIG['zones']` and `DEFAULT_CONFIG['default_zone_name']` propagate to every `get_config` payload via the existing sparse-merge in `async_load` — ready for Phase 6 frontend consumption
- STORAGE_VERSION=2 preserved — no migration path needed

## Self-Check: PASSED

---
*Phase: 04-zone-data-model-storage*
*Completed: 2026-05-27*

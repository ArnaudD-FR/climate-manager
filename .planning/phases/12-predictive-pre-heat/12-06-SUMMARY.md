---
phase: 12-predictive-pre-heat
plan: "06"
subsystem: climate-backend
tags: [python, homeassistant, preheat, zones, websocket, storage-migration]

requires:
  - phase: 12-predictive-pre-heat
    plan: "04"
    provides: "Per-room preheat_enabled toggle (to be corrected by this plan)"

provides:
  - "Zone-scoped preheat_enabled read in _async_preheat_room (coordinator.py)"
  - "set_zone_preheat WS command for Default Zone and custom zones"
  - "Storage migration: legacy room.preheat_enabled → zone scope on async_load"
  - "29 passing tests covering zone-enable, migration, and set_zone_preheat"

affects:
  - "12-07 (frontend must wire zone toggle against set_zone_preheat contract)"

tech-stack:
  added: []
  patterns:
    - "Default Zone top-level key pattern: default_zone_preheat_enabled mirrors\
  \ default_zone_name"
    - "Dual-path WS handler: zone_id='default' routes to top-level key; UUID\
  \ routes to zones dict"
    - "CR-01 snapshot/rollback on every WS write handler"

key-files:
  created: []
  modified:
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/websocket.py
    - custom_components/climate_manager/storage.py
    - custom_components/climate_manager/const.py
    - tests/test_preheat.py

key-decisions:
  - "Option A for Default Zone: top-level default_zone_preheat_enabled key\
  \ mirrors default_zone_name; Default Zone never appears in zones{}"
  - "Dangling zone_id falls back to default_zone_preheat_enabled (defense-in-depth\
  \ identical to _resolve_zone_config)"
  - "Storage migration unconditionally pops deprecated room key (T-12-13) so\
  \ it cannot silently re-gate behaviour after upgrade"

patterns-established:
  - "Zone preheat_enabled (sparse, absent=False) inside zones[uuid] for\
  \ custom zones"
  - "default_zone_preheat_enabled (sparse, absent=False) at runtime_config\
  \ top level for Default Zone rooms"

requirements-completed: [PREHEAT-01, PREHEAT-04]

duration: 35min
completed: 2026-06-03
---

# Phase 12 Plan 06: Zone-Scoped Pre-Heat Enable Summary

**Zone-level preheat_enabled replaces per-room flag: coordinator, WS command,
storage migration, and 29 tests all aligned to zone scope (GAP-01)**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-03T00:00:00Z
- **Completed:** 2026-06-03
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Coordinator `_async_preheat_room` reads `preheat_enabled` from the room's
  zone (custom zone dict or `default_zone_preheat_enabled` top-level key),
  not from `room_config`; `preheat_max_lead_minutes` stays per-room.
- New `set_zone_preheat` WS command (19th command) persists the flag for the
  Default Zone or any custom zone with full CR-01 snapshot/rollback.
- `ws_set_room_config` silently drops incoming `preheat_enabled` so legacy
  callers cannot persist the deprecated room-level key.
- Storage `async_load` migrates any stored `room.preheat_enabled=True` to
  the zone or to `default_zone_preheat_enabled`, then unconditionally pops
  the deprecated key (T-12-13 guard).
- `const.py` schema doc updated: room `preheat_enabled` removed; new zone
  and top-level keys documented.
- All 29 tests in `tests/test_preheat.py` pass (5 new: zone-enable read,
  default-zone-enable read, storage migration, WS set_zone_preheat custom +
  default).

## Task Commits

1. **Task 1: Coordinator reads zone-level preheat_enabled** - `82ef099`
   (feat)
2. **Task 2: WS — add set_zone_preheat, drop room-level enable** - `0d106e9`
   (feat)
3. **Task 3: Storage migration + const docs + tests** - `0dac172` (feat)

## Files Created/Modified

- `custom_components/climate_manager/coordinator.py` — `_async_preheat_room`
  now resolves enable from zone scope via `zone_id` lookup
- `custom_components/climate_manager/websocket.py` — added
  `_make_ws_set_zone_preheat`; removed preheat_enabled coerce from
  `ws_set_room_config`; now 19 commands
- `custom_components/climate_manager/storage.py` — GAP-01 migration loop in
  `async_load` after existing D-02 person-rename loops
- `custom_components/climate_manager/const.py` — schema doc comment updated
  to reflect new zone/default keys; per-room preheat_enabled removed
- `tests/test_preheat.py` — all fixtures/coordinator tests retargeted to
  zone scope; 5 new tests added; 29 total passing

## Decisions Made

- **Option A for Default Zone** (as documented in plan objective): top-level
  `default_zone_preheat_enabled` mirrors `default_zone_name`. Avoids placing
  the Default Zone inside `zones{}` which would break `_resolve_zone_config`
  and `validate_zone_assignment` invariants.
- **Dangling zone_id fallback**: falls back to `default_zone_preheat_enabled`
  identically to `_resolve_zone_config` — no cross-zone data leakage
  (T-12-12 accepted, defense-in-depth).
- **Unconditional pop in migration**: `preheat_enabled` is popped from every
  room regardless of value (not just `True`) so a stored `False` never
  prevents the zone flag from taking effect.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unused variable `temp_calls` in new test**

- **Found during:** Task 3 (tests/test_preheat.py)
- **Issue:** `ruff` F841 linting error: `temp_calls = async_mock_service(...)`
  assigned but not referenced in `test_preheat_reads_zone_enabled`.
- **Fix:** Removed the assignment; `async_mock_service` called without
  binding to a variable (the mock is only needed to intercept calls, not to
  inspect them in this test).
- **Files modified:** `tests/test_preheat.py`
- **Verification:** `make lint` passes; all 29 tests still pass.
- **Committed in:** `0dac172` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — unused variable linting error)
**Impact on plan:** Minor lint-only fix; no scope change.

## Issues Encountered

- `ClimateManagerStorage` was used in the initial migration test; corrected to
  `ClimateManagerStore` (the actual class name in `storage.py`) before
  committing.
- The `make lint` / `make test` commands run from the main repo but pytest
  collects the worktree file when invoked with the full path — ran tests with
  `/home/arnaud/dev/climate_manager/.venv/bin/python -m pytest tests/...`
  from the worktree root to confirm 29 tests collected and passing.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes
at trust boundaries beyond what the plan's threat model covers:
- T-12-11: `set_zone_preheat` vol schema + ERR_NOT_FOUND guard implemented.
- T-12-12: dangling zone_id fallback implemented (accepted in plan).
- T-12-13: migration unconditional pop implemented.

## Known Stubs

None — all zone-scope reads are wired to real config data; no placeholder
values.

## Next Phase Readiness

- Backend contract is stable: coordinator reads zone-level enable, WS command
  persists it, migration handles legacy data.
- Plan 12-07 (frontend) can now wire the zone toggle UI against
  `set_zone_preheat` and remove the per-room toggle.

---
*Phase: 12-predictive-pre-heat*
*Completed: 2026-06-03*

---
phase: 16-presence-heating-log-traces
plan: "07"
subsystem: coordinator
tags: [coordinator, domain-model, eval-context, zone, person, room, trv, trvgroup, refactor]

requires:
  - phase: 16-presence-heating-log-traces/16-02
    provides: EvalContext dataclass with calendar lazy-fetch
  - phase: 16-presence-heating-log-traces/16-03
    provides: TRV + TRVGroup domain classes in trv.py
  - phase: 16-presence-heating-log-traces/16-04
    provides: Person + PersonMode state machine in person.py
  - phase: 16-presence-heating-log-traces/16-05
    provides: Room domain class with preheat/calibration state
  - phase: 16-presence-heating-log-traces/16-06
    provides: Zone + ZoneMode state machine in zone.py

provides:
  - Refactored coordinator.py delegating to domain objects (D-09)
  - _build_domain_objects(config) constructing Zone/Person/Room/TRVGroup graphs
  - async_evaluate using EvalContext + zone loop + per-room preheat pass
  - Dead coordinator methods removed (12 methods deleted)
  - OBS-01 structured log families emitted via domain objects

affects: [coordinator, tests, preheat, calibration, status-payload]

tech-stack:
  added: []
  patterns:
    - "_build_domain_objects(config): fingerprint-based rebuild on WS config changes (T-16-13)"
    - "EvalContext passed through zone -> room -> TRV call chain for per-cycle cache"
    - "Room._preheat_* scalars replace coordinator dict[area_id] preheat state (D-06)"
    - "TRV.last_pushed replaces coordinator._last_pushed dict (Pitfall 5)"

key-files:
  created: []
  modified:
    - custom_components/climate_manager/coordinator.py
    - tests/test_coordinator.py
    - tests/test_preheat.py

key-decisions:
  - "D-09: async_evaluate = EvalContext creation + zone loop + per-room preheat + _async_calibrate(ctx)"
  - "T-16-13: rebuild-on-fingerprint-change so WS mutations are visible next tick"
  - "Kept _async_calibrate for Tado X device-level calibration (Room.calibrate_trvs handles generic entities)"
  - "Preheat status in _build_status_payload reads from Room._preheat_* not coordinator dicts"

requirements-completed: [OBS-01]

duration: 19min
completed: "2026-06-04"
---

# Phase 16 Plan 07: Coordinator Integration Wave Summary

**Refactored coordinator.py to build Zone/Person/Room/TRVGroup domain graphs at
init and delegate evaluate cycle to domain objects via EvalContext, retiring 12
monolithic coordinator methods and wiring all three OBS-01 log families.**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-06-04T21:26:32Z
- **Completed:** 2026-06-04T21:46:00Z
- **Tasks:** 2 of 3 automated (Task 3 is a human checkpoint — pending)
- **Files modified:** 3

## Accomplishments

- Added `_build_domain_objects(config)` method with fingerprint-based
  rebuild-on-change (T-16-13) creating Zone/Person/Room/TRVGroup graphs
- Rewrote `async_evaluate` to D-09 shape: one `EvalContext` per cycle,
  zone evaluation loop, per-room preheat pass, calibration delegation
- Deleted 12 migrated coordinator methods: `_prefetch_calendars`,
  `_compute_desired_temps`, `_apply_presence_overrides`, `_push_temperatures`,
  `_async_preheat`, `_async_preheat_room`, `_async_calibrate_room`,
  `_resolve_zone_config`, `_compute_present_persons`, `_push_safely`,
  `_push_off_safely`, `_push_if_changed`
- Updated tests to use domain objects: `TRV.last_pushed` instead of
  `coordinator._last_pushed`, `Room.compute_preheat(ctx)` instead of
  `coordinator._async_preheat_room`

## Task Commits

1. **Task 1: Instantiate domain objects at coordinator init** - `1b88fff` (feat)
2. **Task 2: Rewrite async_evaluate + delete migrated methods + update tests** - `b761378` (feat)
3. **Task 3: Human verification of OBS-01 log families in live HA** - PENDING CHECKPOINT

## Files Created/Modified

- `custom_components/climate_manager/coordinator.py` - Refactored coordinator:
  _build_domain_objects, EvalContext-based async_evaluate, 12 methods deleted
- `tests/test_coordinator.py` - Updated mock targets: _last_pushed -> TRV.last_pushed
- `tests/test_preheat.py` - Updated: _async_preheat_room -> Room.compute_preheat(ctx)

## Decisions Made

- `_async_calibrate` retained because it handles Tado X device-level calibration
  that Room.calibrate_trvs does not; generic entity path delegated to Room.
- `_frost_locked_rooms` coordinator field retained; Room._frost_locked is the
  per-room analog set by ZoneModeOff evaluation (not wired in this wave).
- `_compute_config_fingerprint` uses `hash(repr(...))` for cheapness; acceptable
  collision risk given evaluation is idempotent on repeated builds.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Unused entity_reg variable in _build_domain_objects**
- **Found during:** Task 1 commit (ruff lint hook)
- **Issue:** `entity_reg = er.async_get(self._hass)` unused; TRVGroup.from_room_config
  imports entity registry internally
- **Fix:** Removed unused variable and import
- **Files modified:** coordinator.py
- **Committed in:** 1b88fff (same task commit)

**2. [Rule 3 - Blocking] _calendar_cache removal cascaded to multiple callers**
- **Found during:** Task 1 implementation
- **Issue:** Removing `self._calendar_cache` from `__init__` required threading
  `calendar_cache` as a local variable through three methods (deleted in Task 2)
- **Fix:** Added `calendar_cache: dict` parameter with `None` fallback;
  threaded from `async_evaluate` local
- **Files modified:** coordinator.py
- **Committed in:** 1b88fff (same task commit)

**3. [Rule 1 - Bug] _async_calibrate_for_room called deleted _async_calibrate_room**
- **Found during:** Task 2 method deletion
- **Issue:** _async_calibrate_for_room (event-driven Matter calibration path)
  referenced _async_calibrate_room which was being deleted
- **Fix:** Updated _async_calibrate_for_room to use Room.calibrate_trvs with a
  minimal EvalContext for non-Tado entity paths; Tado X device path unchanged
- **Files modified:** coordinator.py
- **Committed in:** b761378 (same task commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All fixes necessary for compilation and correctness. No scope creep.

## Known Stubs

None.

## Threat Flags

None.

## Issues Encountered

None beyond the auto-fixed deviations above.

## Next Phase Readiness

- Coordinator is now a thin orchestrator; domain objects own all logic
- OBS-01 log families wired via Person.evaluate, Zone.evaluate, TRV.push_temperature
- Task 3 (human checkpoint) requires deploy + live HA log verification

## Self-Check: PASSED

Files verified:
- `custom_components/climate_manager/coordinator.py`: EXISTS (modified)
- `tests/test_coordinator.py`: EXISTS (modified)
- `tests/test_preheat.py`: EXISTS (modified)
- `16-07-SUMMARY.md`: EXISTS (this file)

Commits verified:
- 1b88fff: feat(16-07): instantiate domain objects at coordinator init
- b761378: feat(16-07): rewrite async_evaluate + delete migrated methods + update tests

Test suite: 279 passed, 0 failed (verified with make test equivalent)

---
*Phase: 16-presence-heating-log-traces*
*Completed: 2026-06-04*

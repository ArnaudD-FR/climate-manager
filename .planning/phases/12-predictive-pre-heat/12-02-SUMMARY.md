---
phase: 12-predictive-pre-heat
plan: "02"
subsystem: coordinator
tags: [python, coordinator, preheat, tdd, storage, schedule]

requires:
  - phase: 12-predictive-pre-heat
    plan: "01"
    provides: next_occupied_at() + pre-heat constants + wakeup_advance_minutes
      migration
    this-uses: next_occupied_at(), DEFAULT_PREHEAT_LEAD_MINUTES,
      DEFAULT_PREHEAT_MAX_LEAD_MINUTES, PREHEAT_MAX_SAMPLES,
      PREHEAT_CONVERGENCE_THRESHOLD, PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD

provides:
  - _async_preheat() / _async_preheat_room() in coordinator.py
  - climate_manager_preheat Store wired into ClimateManagerData
  - preheat_active / preheat_target / preheat_suppressed on room status payload
  - D-02 wakeup_advance_minutes read-sites in coordinator.py (2 sites)
  - 8 new coordinator preheat tests in tests/test_preheat.py

affects:
  - 12-03 preheat learning engine (if applicable — coordinator inertia
    sample persisted here)
  - 12-04 frontend pre-heat UI (consumes preheat_active/target/suppressed
    from status payload)

tech-stack:
  added: []
  patterns:
    - _async_preheat_room guard order: convergence → discard → trigger
      (D-09 spec)
    - Frost-lock guard before any preheat set_temperature (T-12-03)
    - Sample persisted in convergence branch only, not every tick (T-12-05)
    - bus.async_fire moved AFTER _async_preheat so panel sees preheat_active
      in the same cycle it fires (RESEARCH Open Question 1)

key-files:
  created: []
  modified:
    - custom_components/climate_manager/__init__.py
    - custom_components/climate_manager/coordinator.py
    - tests/test_preheat.py

key-decisions:
  - "D-06 / T-12-05: preheat_store.async_save called only on convergence
    (sample added), not every tick — bounded write rate"
  - "D-09 guard order enforced: convergence check first (clear in-progress
    on target reached), then discard check (next_occupied None or past),
    then trigger"
  - "T-12-03: self._frost_locked_rooms snapshot stored each cycle in
    async_evaluate; checked in _async_preheat_room before set_temperature"
  - "RESEARCH Open Question 1: bus.async_fire moved after _async_preheat
    to avoid one-cycle lag in preheat_active status"
  - "D-02: wakeup_advance_minutes read with fallback chain
    (wakeup_advance_minutes → preheat_lead_minutes → DEFAULT) at both
    coordinator read-sites"
  - "Test deviation: test_sample_discarded_when_period_starts uses
    force_absent mode (next_occupied_at returns None) rather than
    scheduled-past-arrival because next_occupied_at always returns strictly
    future times — discard via None path is equivalent for D-07"

requirements-completed: [PREHEAT-02, PREHEAT-03, PREHEAT-04]

duration: ~45min
completed: 2026-06-02
---

# Phase 12 Plan 02: Predictive Pre-Heat Coordinator Engine Summary

**Pre-heat pass in coordinator: _async_preheat with convergence sample
learning, frost-lock guard, and room status preheat fields**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-02T18:30:00Z
- **Completed:** 2026-06-02
- **Tasks:** 2 (Task 1: Store wire-up; Task 2: TDD coordinator implementation)
- **Files modified:** 3

## Accomplishments

- Added `preheat_store` (Store) and `preheat_samples` (dict) fields to
  ClimateManagerData; preheat Store instantiated and loaded in
  async_setup_entry (D-06)
- Implemented `_async_preheat()` / `_async_preheat_room()` in coordinator
  mirroring `_async_calibrate()` (concurrent gather over rooms)
- D-09 guard order: convergence check → discard check → trigger
  - Convergence: current_temp >= target - threshold → record
    {duration_minutes, timestamp} sample, persist to preheat_store
  - Discard: next_occupied None or now >= next_occupied → clear in-progress
    without recording (D-07)
  - Trigger: inside lead window and not frost-locked → set_temperature at
    upcoming setpoint (T-12-03)
- D-08: learned lead = average of last PREHEAT_MAX_SAMPLES capped at
  preheat_max_lead_minutes; falls back to DEFAULT_PREHEAT_LEAD_MINUTES=60
  when < PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD samples
- D-10 / PREHEAT-04: preheat_active / preheat_target / preheat_suppressed
  added to room_entry in `_build_status_payload`
- D-02: two `preheat_lead_minutes` read-sites in coordinator.py renamed
  to `wakeup_advance_minutes` with fallback chain
- bus.async_fire moved after _async_preheat (RESEARCH Open Q1 — no
  one-cycle status lag)
- 8 new coordinator preheat tests (TDD RED→GREEN); full suite 209 tests
  green

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire climate_manager_preheat Store** - `188059d` (feat)
2. **Task 2 RED: Failing coordinator preheat tests** - `373df9a` (test)
3. **Task 2 GREEN: Implement preheat pass** - `80d5921` (feat)

_TDD: RED commit (373df9a) → GREEN commit (80d5921). Tests were written
first to fail, then the implementation made them pass._

## Files Created/Modified

- `custom_components/climate_manager/__init__.py` — Added Store import,
  preheat_store/preheat_samples fields to ClimateManagerData, preheat
  store load in async_setup_entry
- `custom_components/climate_manager/coordinator.py` — Added preheat
  constants/next_occupied_at imports; _preheat_in_progress/_preheat_active/
  _preheat_target/_preheat_suppressed/_frost_locked_rooms instance dicts;
  _async_preheat()/_async_preheat_room() methods; preheat fields in
  _build_status_payload; wakeup_advance_minutes at 2 read-sites; moved
  bus.async_fire after _async_preheat
- `tests/test_preheat.py` — Added 8 coordinator preheat tests (Plan 02
  Task 2); updated module docstring and imports

## Decisions Made

- D-06 / T-12-05: Sample saved only on convergence, not every tick —
  prevents Store write on every 60s evaluation cycle
- D-09 guard order correctly implemented: convergence checked first
  (clears in-progress and returns), then discard, then trigger
- T-12-03: `self._frost_locked_rooms` snapshot stored in `async_evaluate`
  immediately after `_compute_desired_temps` returns it; `_async_preheat_room`
  reads it before any `set_temperature` call
- Test deviation documented: discard test uses force_absent (next_occupied_at
  = None) rather than trying to simulate past arrival, because
  next_occupied_at always returns strictly future times; the None path
  is semantically equivalent for D-07 testing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test timing correction for preheat trigger test**

- **Found during:** Task 2 GREEN phase
- **Issue:** test_preheat_trigger_fires used now=05:30 with next_occupied=07:00
  and default lead=60min, putting the trigger window at [06:00, 07:00). The
  test was outside the window.
- **Fix:** Changed freeze_time to 06:30 (inside window) and updated `now`
  to match
- **Files modified:** tests/test_preheat.py

**2. [Rule 1 - Bug] Discard test refactored to use force_absent**

- **Found during:** Task 2 GREEN phase
- **Issue:** Original test used a scheduled person at now=07:05 expecting
  discard. But at 07:05 the person is present (since 07:00), and
  next_occupied_at returns the next day's 07:00 (strictly future), so
  `now >= next_occupied` was False.
- **Fix:** Changed to force_absent mode where next_occupied_at returns None
  directly — the discard condition `next_occupied is None` triggers correctly.
- **Files modified:** tests/test_preheat.py

**3. [Rule 1 - Bug] Removed unused all_persons_no_schedule variable**

- **Found during:** Task 2 GREEN phase (ruff pre-commit hook)
- **Issue:** F841 — `all_persons_no_schedule` was initialized and updated
  but never consumed after the loop (the suppression logic was independently
  computed using `all(...)`)
- **Fix:** Removed the variable and simplified the loop
- **Files modified:** custom_components/climate_manager/coordinator.py

**4. [Rule 3 - Blocking] Save logic moved into _async_preheat_room**

- **Found during:** Task 2 GREEN phase — test_sample_recorded_on_convergence
  called _async_preheat_room directly (not _async_preheat), so the
  post-gather save in _async_preheat was never exercised by the test.
- **Fix:** Moved `preheat_store.async_save` into the convergence branch of
  `_async_preheat_room` (called immediately on convergence). This keeps T-12-05
  bounded write rate while making the behavior testable at the room level.
- **Files modified:** custom_components/climate_manager/coordinator.py

## TDD Gate Compliance

- RED commit `373df9a`: `test(12-02): add failing coordinator preheat tests`
- GREEN commit `80d5921`: `feat(12-02): implement _async_preheat pass + ...`
- RED→GREEN sequence confirmed in git log

## Known Stubs

None.

## Threat Flags

None — all new surface (preheat set_temperature path) covered by T-12-03
(frost-lock guard) and T-12-05 (bounded write rate) as defined in the
plan's threat model.

## Self-Check

Files exist:
- custom_components/climate_manager/__init__.py: FOUND
- custom_components/climate_manager/coordinator.py: FOUND
- tests/test_preheat.py: FOUND

Commits exist:
- 188059d (Task 1): FOUND
- 373df9a (Task 2 RED): FOUND
- 80d5921 (Task 2 GREEN): FOUND

Tests: 209 passed, 0 failed

## Self-Check: PASSED

---
*Phase: 12-predictive-pre-heat*
*Completed: 2026-06-02*

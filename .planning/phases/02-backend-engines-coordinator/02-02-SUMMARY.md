---
phase: 02-backend-engines-coordinator
plan: "02"
subsystem: coordinator
tags:
  - coordinator
  - control-loop
  - scheduler
  - presence-logic
  - push-on-change
dependency_graph:
  requires:
    - 02-01 (schedule.py — evaluate_schedule, resolve_presence,
      compute_occupied_temp)
    - 01-foundation (__init__.py, trv.py, storage.py, const.py)
  provides:
    - ClimateManagerCoordinator
    - async_evaluate (minute-poll control loop)
    - push-on-change mechanism (_last_pushed dict)
    - manual-override hold
    - startup push (INFRA-03)
    - cancel_scheduler (Pitfall 1 prevention)
  affects:
    - custom_components/climate_manager/__init__.py (extended with coordinator
      wiring)
    - 03-frontend (will call entry.runtime_data.coordinator for WebSocket API)
tech_stack:
  added:
    - homeassistant.helpers.event.async_track_time_interval (minute-polling
      scheduler)
    - homeassistant.util.dt.now() (DST-safe time source)
  patterns:
    - standalone coordinator class (not DataUpdateCoordinator — no entities to
      notify)
    - _last_pushed dict for push-on-change (D-02)
    - present_locked_rooms set for order-independent present-wins rule (D-07)
    - field(default=None) for optional dataclass fields (Pitfall 5)
    - per-entity exception catch so one bad TRV cannot abort the whole tick
key_files:
  created:
    - custom_components/climate_manager/coordinator.py
    - tests/test_coordinator.py
  modified:
    - custom_components/climate_manager/__init__.py
    - tests/test_init.py
decisions:
  - "present_locked_rooms set used for order-independent present-wins logic in
    MODE_TIME_PROGRAM_PRESENCES (D-07)"
  - "Coordinator reads runtime_config via shared reference — Phase 3 in-place
    updates are seen on next tick (Anti-pattern avoided)"
  - "freeze_time marks use UTC 16:30 to produce 08:30 US/Pacific local time
    (test harness timezone)"
  - "Rule 1 auto-fix: present-wins logic rewritten from baseline-comparison to
    present_locked_rooms set after test failure"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-17"
  tasks_completed: 2
  files_changed: 4
---

# Phase 2 Plan 02: ClimateManagerCoordinator Summary

**One-liner:** ClimateManagerCoordinator control loop with
MODE_OFF/TIME_PROGRAM/PRESENCES branching, push-on-change (\_last_pushed),
manual-override hold, and DST-safe dt_util.now() — 56 tests green, zero
regressions.

## Tasks Completed

| Task | Name                                                                  | Commit  | Files                                                                                        |
| ---- | --------------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------- |
| 1    | Implement ClimateManagerCoordinator in coordinator.py                 | 3414f1e | custom_components/climate_manager/coordinator.py                                             |
| 2    | Wire coordinator + scheduler into **init**.py lifecycle and add tests | ada52da | custom_components/climate_manager/**init**.py, tests/test_coordinator.py, tests/test_init.py |
| Fix  | Rule 1 — correct present-wins logic in MODE_TIME_PROGRAM_PRESENCES    | d5315df | custom_components/climate_manager/coordinator.py                                             |

## What Was Built

### coordinator.py — ClimateManagerCoordinator class

`ClimateManagerCoordinator.__init__(hass, data)`:

- Stores `self._hass`, `self._data` (shared reference — sees in-place updates
  from Phase 3)
- Initialises `self._last_pushed: dict[str, float] = {}` (empty on construction
  — D-04)

`async_evaluate(_utc_now=None)`:

- Ignores the `_utc_now` arg; calls `now = dt_util.now()` as single time source
  (Pitfall 2, INFRA-05)
- Branches on `global_mode` from `runtime_config`:
  - `MODE_OFF`: frost protection for all rooms (GLOBAL-02)
  - `MODE_TIME_PROGRAM`: per-room override else global weekday_groups;
    evaluate_schedule + push (SCHED-05)
  - `MODE_TIME_PROGRAM_PRESENCES`: time-program baseline for all rooms, then
    presence override via compute_occupied_temp; present-wins rule via
    `present_locked_rooms` set
- Per-entity exception catch: one failing TRV logs a warning but does not abort
  the tick

`_push_if_changed(entity_id, desired_temp)`:

- D-02: skip if `last == desired_temp` (push-on-change)
- D-03: skip if TRV reports temperature different from `last` (manual override
  hold)
- Pitfall 3: on startup `last=None` → both guards bypass → startup push always
  fires (INFRA-03)
- Pitfall 6: reads `attributes.get("temperature")` (setpoint), not the measured
  room temp

`POLL_INTERVAL = timedelta(minutes=1)` — exported constant for caller use.

### **init**.py — Extended lifecycle wiring

`ClimateManagerData` dataclass extended with:

- `coordinator: "ClimateManagerCoordinator | None" = field(default=None)` —
  avoids Pitfall 5
- `cancel_scheduler: "Callable[[], None] | None" = field(default=None)` — avoids
  Pitfall 5

`async_setup_entry` (new steps after existing runtime_data assignment):

1. Construct `ClimateManagerCoordinator(hass, entry.runtime_data)`
2. `await coordinator.async_evaluate()` — immediate startup push (INFRA-03,
   before first tick)
3. `entry.runtime_data.cancel_scheduler = async_track_time_interval(...)` —
   minute polling (D-01)

`async_unload_entry` (new first step):

- `if entry.runtime_data.cancel_scheduler is not None: entry.runtime_data.cancel_scheduler()`
- Cancel happens BEFORE `async_unload_platforms` (Pitfall 1 — no ghost
  listeners)
- `PLATFORMS` stays `[]` (D-09 — pure backend)

### tests/test_coordinator.py — 5 integration tests (321 lines)

1. `test_coordinator_pushes_on_startup`: at least one `set_temperature` call
   after evaluate (INFRA-03)
2. `test_unload_cancels_scheduler`: cancel_scheduler is not None; unload returns
   True (Pitfall 1)
3. `test_push_on_change_no_duplicate`: second evaluate with same temp → call
   count unchanged (D-02)
4. `test_manual_override_hold`: TRV reports 24.0 after push of 20.0 → entity
   skipped on next evaluate (D-03)
5. `test_present_person_wins_absent_for_same_room`: two persons (one present,
   one absent) share "lounge"; asserts Normal temperature (20.0) received, NOT
   Reduced (18.0) — order-independent (D-07)

### tests/test_init.py — 1 new test added

- `test_setup_entry_coordinator_and_scheduler_wired`: asserts
  `coordinator is ClimateManagerCoordinator` instance and `cancel_scheduler` is
  callable after setup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed order-dependent present-wins logic in
MODE_TIME_PROGRAM_PRESENCES**

- **Found during:** Task 2 (test_present_person_wins_absent_for_same_room
  failure)
- **Issue:** Initial implementation compared
  `current desired_temp <= baseline temp` to detect whether a present person had
  set it. This fails when present person's occupied-window temp equals the
  baseline (e.g., both Normal = 20.0), causing an absent person to incorrectly
  overwrite it with Reduced (18.0).
- **Fix:** Replaced baseline-comparison logic with a
  `present_locked_rooms: set[str]` that explicitly tracks rooms where a present
  person has set the temperature. Absent persons skip locked rooms entirely. The
  fix is order-independent regardless of person iteration sequence.
- **Files modified:** `custom_components/climate_manager/coordinator.py`
- **Commit:** d5315df

**2. [Rule 1 - Bug] Fixed freeze_time marks using wrong UTC time for US/Pacific
test harness**

- **Found during:** Task 2 (debug of present-wins test failure — root cause was
  that freeze_time "2026-01-05 08:30:00" UTC = 00:30 local, putting the test
  before the Normal period's start at 07:00 local)
- **Issue:** `pytest-homeassistant-custom-component` configures `dt_util` with
  US/Pacific timezone (UTC-8). Freezing at "08:30 UTC" gives 00:30 local time,
  which is before the 07:00 Normal period start — so `compute_occupied_temp` for
  a present person returned Reduced, not Normal.
- **Fix:** Changed all freeze_time marks from `"2026-01-05 08:30:00"` to
  `"2026-01-05 16:30:00"` (16:30 UTC = 08:30 US/Pacific), placing the frozen
  clock inside the Normal period window.
- **Files modified:** `tests/test_coordinator.py`
- **Commit:** ada52da (included in original commit)

## Known Stubs

None — the coordinator is fully implemented. No placeholder returns, no
hardcoded empty values flowing to TRV dispatch.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The
coordinator reads from `hass.states.get()` and writes via `set_trv_temperature`
— both are internal HA mechanisms with existing trust boundaries documented in
the plan's threat model (T-02-04 through T-02-08).

Mitigations implemented:

- T-02-04 (UTC arg misuse): `_utc_now` arg ignored, `dt_util.now()` exclusive —
  confirmed by grep (0 occurrences of `_utc_now` used for time)
- T-02-05 (Ghost listener): `cancel_scheduler` stored and called first in unload
  — confirmed by line ordering check
- T-02-06 (Non-float attribute): `reported is not None` guard +
  `float(reported)` conversion + per-entity exception catch

## Self-Check: PASSED

| Check                                                                   | Result |
| ----------------------------------------------------------------------- | ------ |
| custom_components/climate_manager/coordinator.py exists                 | FOUND  |
| custom_components/climate_manager/**init**.py exists                    | FOUND  |
| tests/test_coordinator.py exists                                        | FOUND  |
| tests/test_init.py exists                                               | FOUND  |
| .planning/phases/02-backend-engines-coordinator/02-02-SUMMARY.md exists | FOUND  |
| Commit 3414f1e (Task 1)                                                 | FOUND  |
| Commit ada52da (Task 2)                                                 | FOUND  |
| Commit d5315df (Rule 1 fix)                                             | FOUND  |
| Full test suite (56 tests)                                              | PASSED |

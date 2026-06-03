---
phase: 12-predictive-pre-heat
plan: "01"
subsystem: presence
tags: [python, schedule, storage, preheat, migration, tdd]

requires:
  - phase: 11-calendar-presence-backend
    provides: schedule.py resolve_presence() and calendar presence logic
    this-uses: WEEKDAY_TO_DAY, _parse_time, _parse_events, _parse_calendar_dt,
      PRESENCE_* constants pattern for mode dispatch

provides:
  - next_occupied_at() pure-Python next-transition helper in schedule.py
  - Phase 12 pre-heat constants in const.py (DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
    PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD, PREHEAT_MAX_SAMPLES,
    PREHEAT_CONVERGENCE_THRESHOLD)
  - wakeup_advance_minutes migration in storage.async_load (D-02)
  - tests/test_preheat.py unit test module (11 tests)

affects:
  - 12-02 coordinator pre-heat pass (consumes next_occupied_at + new constants)
  - 12-03 preheat learning engine (uses PREHEAT_MAX_SAMPLES + PREHEAT_CONVERGENCE_THRESHOLD)
  - 12-04 frontend pre-heat UI (displays wakeup_advance_minutes)

tech-stack:
  added: []
  patterns:
    - next_occupied_at() uses 7-day lookahead with target-day ISO-week parity
      for even_odd (not now's week) — mirrors resolve_presence() pattern
    - Storage migration loop after existing mode-rename loop (Pitfall 6 guard)
    - Calendar next-occupied uses _parse_events() helper shared with
      _is_calendar_active()

key-files:
  created:
    - tests/test_preheat.py
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/schedule.py
    - custom_components/climate_manager/storage.py

key-decisions:
  - "D-01: DEFAULT_PREHEAT_MAX_LEAD_MINUTES=120 lives in const.py as sparse
    room-key default alongside existing DEFAULT_PREHEAT_LEAD_MINUTES=60"
  - "D-02: preheat_lead_minutes renamed to wakeup_advance_minutes at async_load
    via pop(); existing wakeup_advance_minutes never overwritten"
  - "D-03: next_occupied_at() dispatches by mode — HA/force_present/force_absent
    return None; scheduled walks 7-day lookahead; calendar reads cache"
  - "D-05: next_occupied_at() is the next-transition value the pre-heat trigger
    condition (now >= next_occupied_at - learned_lead) consumes"

patterns-established:
  - "Mode dispatch in next_occupied_at mirrors resolve_presence() guard order:
    check explicit modes first (HA, force_*), then calendar, then scheduled"
  - "7-day lookahead selects schedule_even/schedule_odd by target_date ISO week
    (not now's week) — critical for even_odd week-boundary correctness"
  - "Storage migration: use .pop() not .get()/.del to atomically rename keys;
    place AFTER sparse-merge loop, not inside DEFAULT_CONFIG"

requirements-completed: [PREHEAT-02, PREHEAT-05]

duration: 25min
completed: 2026-06-02
---

# Phase 12 Plan 01: Predictive Pre-Heat Foundation Summary

**next_occupied_at() pure-Python next-transition helper with 7-day lookahead,
pre-heat constants, and preheat_lead_minutes → wakeup_advance_minutes migration**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-02T17:59:00Z
- **Completed:** 2026-06-02T18:24:34Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added four Phase 12 constants to const.py (DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
  PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD, PREHEAT_MAX_SAMPLES,
  PREHEAT_CONVERGENCE_THRESHOLD) with sparse room-key documentation comment
- Implemented `next_occupied_at()` in schedule.py with full mode dispatch:
  single-schedule 7-day lookahead, even_odd per-target-day ISO-week parity,
  calendar absent/present event boundary, and None for ha/force modes
- Added `preheat_lead_minutes` → `wakeup_advance_minutes` migration in
  storage.async_load() with correct pop() rename and no-overwrite guard
- Created tests/test_preheat.py with 11 unit tests, all green (RED→GREEN TDD)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Phase 12 pre-heat constants to const.py** - `3386c96` (feat)
2. **Task 2: Implement next_occupied_at() in schedule.py** - `8c23de4` (feat)
3. **Task 3: wakeup_advance_minutes migration in storage.py** - `59888c0` (feat)

_Note: TDD plan — RED→GREEN for Tasks 2 and 3 (tests written first,
ImportError/assertion failures confirmed, then implementation added)_

## Files Created/Modified

- `custom_components/climate_manager/const.py` - Added 4 Phase 12 constants
  and sparse room-key docs comment
- `custom_components/climate_manager/schedule.py` - Added next_occupied_at()
  public function + _next_occupied_calendar() + _next_occupied_scheduled()
  private helpers; added PRESENCE_HA + PRESENCE_CALENDAR to const imports
- `custom_components/climate_manager/storage.py` - Added D-02 migration loop
  after existing person mode-rename loop
- `tests/test_preheat.py` - New file: 8 next_occupied tests + 3 migration tests

## Decisions Made

- D-01: DEFAULT_PREHEAT_MAX_LEAD_MINUTES=120 added next to existing
  DEFAULT_PREHEAT_LEAD_MINUTES=60 (both needed — max lead is the room-level
  cap, default lead is the per-person starting value)
- D-02: Migration uses `.pop("preheat_lead_minutes")` to atomically rename;
  only runs when wakeup_advance_minutes is absent to avoid overwriting a
  user-set value; placed after existing mode-rename loop per Pitfall 6
- D-03: next_occupied_at() dispatches exactly as resolve_presence() does:
  force modes → None, calendar → event boundary, scheduled → period start
- even_odd week selection uses `target_date.isocalendar().week % 2` (not
  `now.date().isocalendar().week % 2`) — same fix as resolve_presence()

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- ruff pre-commit hook reformatted test_preheat.py and schedule.py after first
  commit attempt (removed unused imports, reformatted). Files were re-staged
  and committed successfully on second attempt. Tests remained green.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Next Phase Readiness

- next_occupied_at() is ready for consumption by 12-02 coordinator pre-heat pass
- Pre-heat constants (DEFAULT_PREHEAT_MAX_LEAD_MINUTES, PREHEAT_MAX_SAMPLES, etc.)
  are importable for the learning engine (12-03)
- wakeup_advance_minutes migration is live — existing stored data will auto-rename
  at next load; frontend (12-04) can read the new key name directly
- No blockers for Wave 2

---
*Phase: 12-predictive-pre-heat*
*Completed: 2026-06-02*

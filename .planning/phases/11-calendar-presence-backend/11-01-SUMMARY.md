---
phase: 11-calendar-presence-backend
plan: "01"
subsystem: schedule-engine
tags: [calendar, presence, tdd, pure-python]
dependency_graph:
  requires: []
  provides:
    - "PRESENCE_CALENDAR constant in const.py"
    - "DEFAULT_PREHEAT_LEAD_MINUTES constant in const.py"
    - "resolve_calendar_presence() pure helper in schedule.py"
    - "_parse_calendar_dt() helper for DATE/DATETIME event strings"
    - "calendar_cache param on resolve_presence() for period state 'calendar'"
  affects:
    - custom_components/climate_manager/schedule.py
    - custom_components/climate_manager/const.py
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN: test first, then implementation"
    - "Callable injection for dt_util.start_of_local_day — preserves pure-Python contract"
    - "Optional calendar_cache param on resolve_presence() (RESEARCH Option A)"
key_files:
  created:
    - tests/test_calendar.py
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/schedule.py
decisions:
  - "Callable injection for start_of_local_day avoids homeassistant import in schedule.py (Landmine 4)"
  - "Optional calendar_cache dict param on resolve_presence() follows RESEARCH Option A — minimal footprint"
  - "event_end <= now+lead is the inclusive boundary for pre-heat trigger (D-10)"
metrics:
  duration_minutes: 4
  completed_date: "2026-06-02"
  tasks_completed: 3
  files_modified: 3
  tests_added: 11
requirements: [CAL-01, CAL-03, CAL-04]
---

# Phase 11 Plan 01: Calendar Presence Resolution Layer Summary

**One-liner:** Pure-Python calendar presence resolution with pre-heat lead
time, all-day event parsing, and calendar period state in resolve_presence().

## What Was Built

Added the deterministic core of the calendar presence feature to the existing
schedule engine:

1. **`const.py` additions** — `PRESENCE_CALENDAR = "calendar"` (D-03) and
   `DEFAULT_PREHEAT_LEAD_MINUTES: int = 60` (D-10). Schema comment block
   extended to document the sparse `calendar_config` and `preheat_lead_minutes`
   keys (D-08/D-09). Neither key added to `DEFAULT_CONFIG` (additive sparse
   schema).

2. **`schedule.py` — `_parse_calendar_dt()`** — Module-level helper that
   dispatches on `"T"` in the string: timed events use
   `datetime.datetime.fromisoformat()`, all-day DATE strings use
   `datetime.date.fromisoformat()` then `start_of_local_day(d)` (Landmine 3:
   never compare naive vs aware). `start_of_local_day` is injected as a
   callable so schedule.py imports nothing from homeassistant.

3. **`schedule.py` — `resolve_calendar_presence()`** — Public pure helper
   implementing the full event_means × active × preheat table (CAL-01,
   CAL-04, D-10). Skips events with missing start/end (T-11-01 threat
   mitigation). Pre-heat: `event_end <= now + timedelta(minutes=preheat)` is
   inclusive at the boundary (event ending in exactly `preheat` minutes
   triggers heating).

4. **`schedule.py` — `resolve_presence()` extended** — New optional params
   `calendar_cache: dict | None = None` and `start_of_local_day=None`. In the
   period walk, when `active_state == "calendar"`, reads the active period's
   own `calendar_config` (entity_id, event_means), looks up cached events, and
   delegates to `resolve_calendar_presence()` (CAL-03, D-06). All existing
   positional-call sites remain unaffected (backward-compatible signature).

5. **`tests/test_calendar.py`** — 11 pure unit tests covering all plan
   behaviors: constants, event_means × active × preheat table (4 combos),
   preheat boundary (inclusive/exclusive), all-day event DATE parsing,
   period state resolution with cache hit/miss, regression guard for
   present/absent periods.

## TDD Gate Compliance

- RED commit (`506c949`): `test(11-01)` — failing test file written first
- GREEN commit (`1f0952c`): `feat(11-01)` — implementation making all tests pass

Both gates present in git log.

## Verification Results

```
tests/test_calendar.py  — 11 passed
tests/test_schedule.py  — 38 passed (regression: zero failures)
schedule.py HA imports  — 0 (grep -c "from homeassistant" = 0)
make lint               — Passed (ruff, ruff-format, prettier, markdownlint)
```

## Deviations from Plan

None - plan executed exactly as written.

The `datetime` import line was removed from `tests/test_calendar.py` by ruff
(unused import — `dt_util.now()` was used instead of `datetime.datetime.now()`
everywhere). This is a linter correction, not a functional deviation.

## Known Stubs

None — no UI rendering, no hardcoded empty values that block plan goals. The
`start_of_local_day=None` default in the new helpers uses a UTC fallback only
for pure tests; production coordinators (Plan 02) will always pass
`dt_util.start_of_local_day`.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries.
The T-11-01 and T-11-02 mitigations from the plan's threat register are
implemented:

- **T-11-01** (malformed event start/end): `if not start_s or not end_s:
  continue` in `resolve_calendar_presence()`.
- **T-11-02** (naive-vs-aware TypeError on all-day events): `_parse_calendar_dt`
  converts DATE-only strings via `start_of_local_day` callable; regression
  tested by `test_allday_event_handling`.

## Self-Check

### Files Exist

- [x] `tests/test_calendar.py` — created
- [x] `custom_components/climate_manager/const.py` — modified
- [x] `custom_components/climate_manager/schedule.py` — modified

### Commits Exist

- [x] `506c949` — RED test commit
- [x] `1f0952c` — GREEN implementation commit

## Self-Check: PASSED

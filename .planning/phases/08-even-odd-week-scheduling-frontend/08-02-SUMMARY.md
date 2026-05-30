---
phase: 08-even-odd-week-scheduling-frontend
plan: "02"
subsystem: ui
tags: [typescript, lit, even-odd, week-switcher, schedule-type, tdd]

# Dependency graph
requires:
  - phase: 08-even-odd-week-scheduling-frontend
    plan: "01"
    provides: "getISOWeekNumber/getWeekParity in week-parity.ts, \
re-exported from person-card.ts"
  - phase: 07-even-odd-week-scheduling-backend
    provides: "schedule_type/schedule_even/schedule_odd on PersonConfig, \
setPersonConfig WS accepts partial payload"
provides:
  - "person-card.ts: _activeWeek @state + ISO-parity init on expand (D-09,
    D-10)"
  - "person-card.ts: _daysEven/_daysOdd memoized getters (D-13)"
  - "person-card.ts: _onScheduleTypeChange sends {schedule_type} only (D-04,
    D-05)"
  - "person-card.ts: _onSchedulePeriodsChanged with even/odd branch (D-11,
    D-12)"
  - "person-card.ts: _onResetSchedule with per-week field (D-14, D-15)"
  - "person-card.ts: Schedule type native <select> inside isScheduled block
    (D-01, D-02, D-03)"
  - "person-card.ts: [Even][Odd] CSS button-tab switcher (D-06, D-07, D-08)"
  - "person-card.ts: dynamic resetLabel and week-scoped .days binding"
affects:
  - future phases modifying person-card.ts

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual memoized getter pairs (_daysEven/_daysOdd) cloned from _days\
 pattern"
    - "Scoped .week-switcher CSS inside component styles — same .tab-btn\
 pattern as main.ts"
    - "Render locals (scheduleType, isEvenOdd, resetLabel) computed once per\
 render cycle, no function calls in template"

key-files:
  created: []
  modified:
    - frontend/src/components/person-card.ts

key-decisions:
  - "Import getWeekParity via import{} + export{} form (not re-export only)\
 — the re-export form does not bring the name into scope for class method\
 use; explicit import is required"
  - "Schedule-hint paragraph added below Even/Odd switcher showing current\
 ISO week number + parity — helps users confirm which real dates are Even/Odd\
 (Claude's discretion per CONTEXT.md)"
  - "No guard on _onScheduleTypeChange for empty value (unlike _onModeChange)\
 — the <select> always has one of the two valid option values selected; an\
 empty value cannot occur"

patterns-established:
  - "import + export{} pattern for re-exporting with local use: import\
 {fn} from './module.js'; export {fn};"

requirements-completed: [SCHED-04]

# Metrics
duration: 16min
completed: "2026-05-30"
---

# Phase 08 Plan 02: Even/Odd Week Scheduling UI Summary

**Schedule-type native `<select>`, [Even][Odd] CSS button-tab switcher,
memoized dual day-array getters, week-scoped save/reset handlers, and
dynamic reset label — all wired into `person-card.ts` per D-01 through
D-15**

## Performance

- **Duration:** 16 min
- **Started:** 2026-05-30T06:00:00Z
- **Completed:** 2026-05-30T06:16:18Z
- **Tasks:** 2 (both TDD — build-verified TypeScript)
- **Files modified:** 1 (person-card.ts only)

## Accomplishments

- `@state() _activeWeek: "even"|"odd"` reinitialized from
  `getWeekParity(new Date())` every time the card expands (D-09, D-10)
- `_daysEven` / `_daysOdd` memoized getters cloned from the existing `_days`
  pattern, reading `config.schedule_even` / `config.schedule_odd` (D-13)
- `_onScheduleTypeChange` sends only `{ schedule_type: newType }` — no
  schedule payload; backend seeds/preserves both week schedules (D-04, D-05)
- `_onSchedulePeriodsChanged` writes `schedule_even`, `schedule_odd`, or
  `schedule` depending on `isEvenOdd` + `_activeWeek` — never both (D-11,
  D-12, T-08-04 threat mitigation)
- `_onResetSchedule` sends `{[field]: DEFAULT_SCHEDULE}` scoped to the
  active week only (D-14, D-15)
- Native `<select class="mode-select">` with "Single week" / "Even / Odd
  weeks" options inside the `isScheduled` block (D-01, D-02, D-03)
- `<div class="week-switcher">` with [Even][Odd] `.tab-btn` / `.tab-btn.active`
  rendered only when `isEvenOdd` (D-06, D-07, D-08)
- Schedule-hint paragraph showing current ISO week number + parity
- Dynamic `${resetLabel}` in template — "Reset Even/Odd week to default"
  or "Reset to default" (D-15)
- Scoped `.week-switcher` CSS matching `main.ts` `.tab-btn` pattern

## Task Commits

1. **Task 1: State, dual memoization, and per-week save/reset handlers**
   `5eeae4c` (feat)
2. **Task 2: Render template integration and scoped week-switcher CSS**
   `cef396d` (feat)

## Files Created/Modified

- `frontend/src/components/person-card.ts` — Added `_activeWeek` state,
  `_daysEven`/`_daysOdd` getters, `updated()` hook extension,
  `_onScheduleTypeChange`, updated `_onResetSchedule` and
  `_onSchedulePeriodsChanged`, schedule-type select HTML, Even/Odd
  switcher HTML, week-scoped `.days` binding, dynamic `${resetLabel}`,
  scoped `.week-switcher` CSS

## Decisions Made

- **import + export{} for local use:** `export { fn } from "./module.js"`
  is a re-export that does not bind the name in the local module scope.
  Added `import { getISOWeekNumber, getWeekParity } from "./week-parity.js"`
  before the `export {}` line so the class can call `getWeekParity` and
  `getISOWeekNumber` directly.
- **Schedule-hint with ISO week number:** Added a `<p class="schedule-hint">`
  showing `Week N is currently active (even/odd week)` below the switcher
  when `isEvenOdd`. This gives users concrete context about which calendar
  dates are "Even" — Claude's discretion per CONTEXT.md.
- **No empty-value guard in _onScheduleTypeChange:** Unlike `_onModeChange`
  which guards `if (!newMode) return`, the schedule-type select always has
  exactly one of "single" / "even_odd" selected; an empty value is not
  possible from this `<select>`.

## Deviations from Plan

None — plan executed exactly as written. The prettier pre-commit hook
reformatted the file on the Task 1 commit (same as Plan 01 experience),
which was expected and re-staged automatically before the second commit
attempt succeeded.

## Issues Encountered

- Pre-commit prettier hook reformatted file on first commit attempt. Re-staged
  and committed on second attempt — same pattern as Plan 01. No code impact.

## Threat Surface Scan

No new attack surface introduced. The schedule-type `<select>` sends only
`"single"` or `"even_odd"` (TypeScript union constraint). Backend treats any
non-`"even_odd"` value as `"single"` (T-08-02 mitigated). The Even/Odd
switcher writes exactly one of `schedule_even` XOR `schedule_odd` per edit,
never both (T-08-04 mitigated). No new WebSocket commands, no new trust
boundaries.

## Known Stubs

None. All bindings are wired to live config fields. The `schedule_even` and
`schedule_odd` fields are populated by the backend seeding logic (Phase 7)
when a person switches to even/odd mode.

## Next Phase Readiness

- SCHED-04 fully implemented: schedule-type select, Even/Odd switcher,
  week-scoped time-bar edits, per-week reset, ISO-parity default tab
- `person-card.ts` build is clean (`npm run build` exits 0)
- No blockers for Phase 9 (TRV calibration) or any remaining Phase 8 work

---

*Phase: 08-even-odd-week-scheduling-frontend*
*Completed: 2026-05-30*

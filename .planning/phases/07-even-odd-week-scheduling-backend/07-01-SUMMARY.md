---
phase: 07-even-odd-week-scheduling-backend
plan: "01"
subsystem: backend-schedule
tags: [schedule, presence, even-odd, tdd, sched-02, sched-03]
dependency_graph:
  requires: []
  provides:
    - resolve_presence() even/odd week selection (SCHED-02)
    - PersonConfig TypeScript types for schedule_type/even/odd (SCHED-01, SCHED-03)
  affects:
    - custom_components/climate_manager/schedule.py
    - custom_components/climate_manager/const.py
    - frontend/src/types.ts
    - tests/test_schedule.py
tech_stack:
  added: []
  patterns:
    - ISO week parity selection via now.date().isocalendar().week % 2
    - Pure Python schedule evaluation (no HA imports)
    - TDD RED/GREEN cycle
key_files:
  created: []
  modified:
    - tests/test_schedule.py
    - custom_components/climate_manager/schedule.py
    - custom_components/climate_manager/const.py
    - frontend/src/types.ts
decisions:
  - "Use now.date().isocalendar().week (named attribute) rather than [1]
    for clarity per CONTEXT.md spec"
  - "week_parity == 0 → even → schedule_even; parity == 1 → odd →
    schedule_odd; else branch unchanged for backward compat"
  - "Comment-only change in const.py (no logic/constants) to document
    three new person fields"
metrics:
  duration_seconds: 200
  completed: "2026-05-29"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 7 Plan 01: Even/Odd Week Schedule Backend Summary

## One-liner

ISO week parity selection in `resolve_presence()` — even_odd persons pick
`schedule_even` or `schedule_odd` based on `now.date().isocalendar().week % 2`.

## What Was Built

Extended `resolve_presence()` in `schedule.py` so persons with
`schedule_type == "even_odd"` are evaluated against `schedule_even` during
even ISO weeks (parity 0) and `schedule_odd` during odd ISO weeks (parity 1).
Persons without `schedule_type` or with `schedule_type == "single"` retain
exact existing behaviour — zero migration needed.

Documented the three new person fields (`schedule_type`, `schedule_even`,
`schedule_odd`) in the const.py persons sub-schema comment block (SCHED-01/03)
and added three corresponding optional fields to the `PersonConfig` TypeScript
interface in `types.ts` (forward-compatible for Phase 8 UI work).

## Commits

| Hash    | Type    | Description                                               |
| ------- | ------- | --------------------------------------------------------- |
| 3737a90 | test    | RED: add failing even/odd week resolve_presence tests     |
| 2ca2900 | feat    | GREEN: implement even/odd week selection in resolve_presence() |
| 4cd9231 | feat    | Document new person fields in const.py and extend PersonConfig types |

## Tasks

### Task 1: RED+GREEN — even/odd week selection in resolve_presence()

**Status:** Complete

**RED phase:** Added `ALWAYS_PRESENT_SCHEDULE` and `ALWAYS_ABSENT_SCHEDULE`
fixtures, then 5 test functions:
- `test_resolve_presence_even_odd_even_week_uses_schedule_even` (T-07-S1)
- `test_resolve_presence_even_odd_odd_week_uses_schedule_odd` (T-07-S2)
- `test_resolve_presence_no_schedule_type_uses_schedule` (T-07-S3)
- `test_resolve_presence_explicit_single_uses_schedule` (T-07-S4)
- `test_resolve_presence_even_odd_missing_week_schedule_returns_false` (T-07-S5)

S1 failed as expected (new code path); S2/S3/S4/S5 already returned the
expected value via the old code path (coincidental pass, not pre-existing
implementation).

**GREEN phase:** Replaced the single `schedule = person_config.get("schedule",
{})` line with the week-parity selection block. All 5 tests pass; full suite
moved from 127 to 132 passed (pre-existing failure in
`test_phase06_acceptance.py` unchanged).

### Task 2: Document new person fields in const.py and extend PersonConfig types

**Status:** Complete

- `const.py`: Added annotation `# used when schedule_type == "single"
  (default)` to the `schedule` entry; added documented entries for
  `schedule_type`, `schedule_even`, `schedule_odd` (SCHED-01/03). Pure
  comment change — no logic added.
- `types.ts`: Extended `PersonConfig` with three optional fields typed against
  the existing `DailyProgram` type. Frontend build confirmed TypeScript
  compiles with no errors.
- `make lint` passes for all modified files.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan adds no UI rendering or data display paths. The three new
`PersonConfig` fields in `types.ts` are intentional forward stubs for Phase 8
UI; they are documented as such in the plan and do not block Plan 01's goal.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes
at trust boundaries beyond what the plan's `<threat_model>` already covers
(T-07-01 through T-07-03).

## Self-Check: PASSED

| Item | Status |
| ---- | ------ |
| tests/test_schedule.py | FOUND |
| schedule.py | FOUND |
| const.py | FOUND |
| frontend/src/types.ts | FOUND |
| 07-01-SUMMARY.md | FOUND |
| commit 3737a90 (RED) | FOUND |
| commit 2ca2900 (GREEN) | FOUND |
| commit 4cd9231 (Task 2) | FOUND |

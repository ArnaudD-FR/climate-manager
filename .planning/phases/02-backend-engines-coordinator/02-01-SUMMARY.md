---
phase: 02-backend-engines-coordinator
plan: "01"
subsystem: schedule-engine
tags:
  - pure-python
  - schedule-evaluation
  - presence-logic
  - tdd
dependency_graph:
  requires:
    - 01-foundation
  provides:
    - evaluate_schedule
    - resolve_presence
    - compute_occupied_temp
    - validate_7day_coverage
    - PRESENCE_AUTOMATIC
    - PRESENCE_PRESENT
    - PRESENCE_ABSENT
  affects:
    - custom_components/climate_manager/coordinator.py (Plan 02-02 calls these
      functions)
tech_stack:
  added: []
  patterns:
    - pure-Python datetime arithmetic (no HA imports in schedule.py)
    - TDD RED/GREEN cycle with direct datetime injection (no freezegun needed)
    - PERIOD_* and PRESENCE_* constant imports (no bare string literals)
key_files:
  created:
    - custom_components/climate_manager/schedule.py
    - tests/test_schedule.py
  modified:
    - custom_components/climate_manager/const.py
decisions:
  - "D-05: present person + no N/C periods today → Reduced temperature (not
    frost protection)"
  - "D-06: validate_7day_coverage enforces exactly-one coverage; both
    missing-day and duplicate-day cases return (False, message)"
  - "Pitfall 4 confirmed: period boundary comparison uses >= so 07:00 exact
    belongs to the new period"
  - "PERSON-08 gap-fill: walk periods tracking last_nc_mode_seen; active Reduced
    inside occupied window substitutes preceding N/C temperature"
metrics:
  duration: "4 minutes"
  completed: "2026-05-17"
  tasks_completed: 2
  files_changed: 3
---

# Phase 2 Plan 01: Schedule and Presence Evaluation Engine Summary

**One-liner:** Pure-Python schedule evaluation engine with PERSON-07/08/09
occupied-window gap-fill, 7-day coverage validator, and 3 presence mode
constants — 32 tests, zero HA imports.

## Tasks Completed

| Task      | Name                                    | Commit  | Files                                         |
| --------- | --------------------------------------- | ------- | --------------------------------------------- |
| 1         | Add presence mode constants to const.py | 86ddbca | custom_components/climate_manager/const.py    |
| 2 (RED)   | Failing tests for schedule engine       | 9d2b742 | tests/test_schedule.py                        |
| 2 (GREEN) | Implement schedule.py evaluation engine | f4a3d24 | custom_components/climate_manager/schedule.py |

## What Was Built

### const.py — 3 new presence mode constants

Added `PRESENCE_AUTOMATIC`, `PRESENCE_PRESENT`, `PRESENCE_ABSENT` with values
`"automatic"`, `"present"`, `"absent"`. Placed after `PERIOD_COMFORT` and before
the Default values block, matching the file's `# ---` comment-header grouping
convention. No HA imports. No existing constants changed.

This resolves Pitfall 7: presence modes were string values in the storage schema
but were never defined as importable constants — leading to scattered string
literals across coordinator.py and schedule.py.

### schedule.py — 4 pure-Python evaluation functions

`evaluate_schedule(weekday_groups, now) -> str`

- Finds today's weekday group, sorts periods by start, walks forward keeping the
  last period whose `start <= now.time()` (>= comparison per Pitfall 4).
- Returns the active period's mode string, falling back to
  `PERIOD_FROST_PROTECTION` if no period has started yet or no group covers
  today.

`resolve_presence(person_config, now) -> bool`

- Short-circuits for `PRESENCE_PRESENT` (True) and `PRESENCE_ABSENT` (False).
- For `PRESENCE_AUTOMATIC`: reads person's `schedule.weekday_groups`, returns
  False if empty (PERSON-05), otherwise evaluates the active state == "present".
- Missing `mode` key defaults to automatic.

`compute_occupied_temp(weekday_groups, now, is_present, period_temperatures) -> float`

- Absent → `period_temperatures[PERIOD_REDUCED]` (PERSON-09).
- No Normal/Comfort periods today → `period_temperatures[PERIOD_REDUCED]`
  (D-05).
- Before/after occupied window → `period_temperatures[PERIOD_REDUCED]`.
- Inside occupied window: walks periods tracking `last_nc_mode_seen`; if active
  period is Reduced/Frost, substitutes the preceding N/C period's temperature
  (PERSON-08 gap-fill).

`validate_7day_coverage(weekday_groups) -> tuple[bool, str]`

- Duplicates → `(False, "Duplicate day assignment in weekday groups")`.
- Missing or unknown days →
  `(False, "Missing days: [...]; Unknown days: [...]")`.
- Valid full coverage → `(True, "")`.

### tests/test_schedule.py — 32 unit tests

Covers all branches of all four functions. Key tests:

- Pitfall 4 regression: exact 07:00 boundary returns the new period's mode (not
  the prior mode).
- PERSON-08 gap-fill: sandwiched Reduced at 12:30 between Normal (07:00) and
  Comfort (14:00) returns Normal temperature.
- PERSON-08 boundary: at 22:30 (after last N/C period ends) returns Reduced
  temperature.
- D-06: separate test cases for missing-day and duplicate-day validation.
- PERSON-05: automatic mode with empty weekday_groups returns False.
- No hass fixture; no freezegun; datetime objects passed directly.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

| Gate     | Commit  | Status                                                             |
| -------- | ------- | ------------------------------------------------------------------ |
| RED      | 9d2b742 | `test(02-01): add failing tests for schedule evaluation engine`    |
| GREEN    | f4a3d24 | `feat(02-01): implement schedule.py pure-Python evaluation engine` |
| REFACTOR | —       | Not needed; code was clean after GREEN                             |

Both required gates present in git history. No REFACTOR gate required.

## Known Stubs

None — all four functions are fully implemented. No placeholder values, no TODO
comments, no hardcoded empty returns that affect the coordinator's behavior.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes
introduced. `schedule.py` is a pure-Python transform module (datetime → period
mode / temperature float). The threat mitigations in the plan's STRIDE register
are addressed:

- T-02-01 (Tampering — overlapping/missing days): `validate_7day_coverage`
  implemented and tested for both missing-day and duplicate-day cases.
- T-02-02 (DoS — malformed period start string): accepted per threat register;
  `_parse_time` will raise `ValueError` on malformed input, to be caught by
  coordinator tick logging (Plan 02-02 scope).
- T-02-03 (Information Disclosure): no I/O, no logging, no PII — confirmed.

## Self-Check

Verified after writing summary.

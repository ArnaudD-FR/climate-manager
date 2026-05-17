---
phase: 03-websocket-api-frontend-panel
plan: "01"
subsystem: backend-schema
tags: [refactor, schema, per-day, schedule, coordinator, tests]
dependency_graph:
  requires: []
  provides: [per-day-schema-D01, validate_daily_program, WEEKDAY_TO_DAY, STORAGE_VERSION_2]
  affects: [03-02-websocket-api, 03-03-frontend-panel]
tech_stack:
  added: []
  patterns: [per-day-dict-schema, direct-dict-lookup, WEEKDAY_TO_DAY-reverse-mapping]
key_files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/schedule.py
    - custom_components/climate_manager/coordinator.py
    - tests/test_schedule.py
    - tests/test_coordinator.py
    - tests/test_storage.py
decisions:
  - "STORAGE_VERSION bumped to 2 with no migration (no production users per RESEARCH Open Question 3)"
  - "Per-day dict lookup via WEEKDAY_TO_DAY[now.weekday()] replaces linear weekday_groups group scan"
  - "validate_daily_program replaces validate_7day_coverage — simpler logic for dict key validation"
  - "DOMAIN added to coordinator.py imports for Wave 2 status push readiness"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-18"
  tasks: 2
  files: 6
---

# Phase 3 Plan 1: Per-Day Schema Refactor (D-01 Gap Closure) Summary

Per-day dict schema `{"mon":[...],...,"sun":[...]}` replaces the `weekday_groups` list-of-groups structure across the entire Phase 2 backend — enabling Phase 3 WebSocket API and frontend panel work which are designed exclusively against the per-day schema.

## What Was Built

Mandatory gap-closure refactor converting all Phase 2 backend files from the `weekday_groups` list-of-groups time-program schema to the per-day dict schema locked by CONTEXT.md decision D-01. No new features were added — behavioral equivalence is preserved with the existing test assertions unchanged in intent.

### Task 1: const.py and schedule.py

**const.py changes:**
- `STORAGE_VERSION` bumped from 1 to 2
- Added `import copy`, `_DAYS_ORDERED`, and `_EMPTY_DAILY_PROGRAM = {day: [] for day in _DAYS_ORDERED}`
- `DEFAULT_CONFIG["global_time_program"]` changed from `{"weekday_groups": []}` to `copy.deepcopy(_EMPTY_DAILY_PROGRAM)`
- Module docstring rewritten: rooms sub-schema documents per-day dict format; persons sub-schema updated; optional `temperature_sensor`/`humidity_sensor` room keys documented (D-16)

**schedule.py changes:**
- Added `WEEKDAY_TO_DAY: dict[int, str] = {v: k for k, v in DAY_TO_WEEKDAY.items()}` reverse mapping
- `evaluate_schedule` signature: `weekday_groups: list[dict]` → `daily_program: dict[str, list]`; uses `daily_program.get(WEEKDAY_TO_DAY[now.weekday()], [])` direct lookup
- `resolve_presence`: `schedule.get("weekday_groups", [])` → `schedule.get(WEEKDAY_TO_DAY[now.weekday()], [])`
- `compute_occupied_temp` signature: `weekday_groups: list[dict]` → `daily_program: dict[str, list]`; `for group in weekday_groups` loop replaced with `sorted(daily_program.get(day_name, []), ...)`
- `validate_7day_coverage` replaced with `validate_daily_program(daily_program: dict[str, list])` using set-difference logic

### Task 2: coordinator.py and all test files

**coordinator.py changes:**
- Added `DOMAIN` import for Wave 2 status push readiness
- `_evaluate_time_program`: `config["global_time_program"]["weekday_groups"]` → `config["global_time_program"]` (IS the per-day dict); room override `.get("time_program", {}).get("weekday_groups")` → `.get("time_program")`
- `_evaluate_time_program_presences`: identical pattern replacement in both baseline loop and person override loop

**test_schedule.py:** Per-day dict fixtures (WEEKDAY_PROGRAM, FULL_WEEK_PROGRAM, PERSON_SCHEDULE), `validate_daily_program` import replaces `validate_7day_coverage`, new WEEKDAY_TO_DAY test, updated resolve_presence fixture (empty dict instead of `{weekday_groups: []}`)

**test_coordinator.py:** Per-day dict fixtures (ALL_DAYS_NORMAL_PROGRAM, TYPICAL_WEEKDAY_PROGRAM, LATE_START_PROGRAM using dict comprehensions), `_make_runtime_config` uses `daily_program` parameter (not `weekday_groups`), `version: 2`, persons schedules use `{}`

**test_storage.py:** Room `time_program` fixture uses `{d: [] for d in days}` per-day dict

## Test Results

```
58 passed in 1.04s  (pytest tests/)
0 weekday_groups occurrences in custom_components/ and tests/
STORAGE_VERSION == 2
DEFAULT_CONFIG["global_time_program"] == {d: [] for d in ["mon","tue","wed","thu","fri","sat","sun"]}
validate_daily_program rejects missing and unknown day keys
```

## Deviations from Plan

None — plan executed exactly as written. All task actions, file targets, and acceptance criteria were met without deviation.

## Known Stubs

None — this is a pure refactor. All schedule/presence/coordinator logic produces identical heating behavior to before; no UI or data stubs introduced.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. This refactor tightens the schema (per-day dict with validated keys) and is covered by existing threat register entries T-03-01 and T-03-02 which were implemented as specified:
- T-03-01: `daily_program.get(day_name, [])` returns `[]` for missing keys → PERIOD_FROST_PROTECTION fallback
- T-03-02: per-entity `try/except` in coordinator already isolates push failures

## Self-Check: PASSED

- `/home/arnaud/dev/climate_manager/custom_components/climate_manager/const.py` — FOUND
- `/home/arnaud/dev/climate_manager/custom_components/climate_manager/schedule.py` — FOUND
- `/home/arnaud/dev/climate_manager/custom_components/climate_manager/coordinator.py` — FOUND
- `/home/arnaud/dev/climate_manager/tests/test_schedule.py` — FOUND
- `/home/arnaud/dev/climate_manager/tests/test_coordinator.py` — FOUND
- `/home/arnaud/dev/climate_manager/tests/test_storage.py` — FOUND
- Commit cd7f566 — FOUND (Task 1: const.py + schedule.py + test_schedule.py)
- Commit f6421a5 — FOUND (Task 2: coordinator.py + test_coordinator.py + test_storage.py)
- `pytest tests/` — 58 passed
- `grep weekday_groups custom_components/ tests/` — 0 matches

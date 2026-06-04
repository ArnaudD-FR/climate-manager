---
phase: 16-presence-heating-log-traces
plan: "01"
subsystem: test-scaffolding
tags: [tdd, red-phase, domain-model, obs-01]
dependency_graph:
  requires: []
  provides:
    - tests/test_eval_context.py
    - tests/test_zone.py
    - tests/test_person.py
    - tests/test_room_domain.py
  affects:
    - custom_components/climate_manager/eval_context.py (not yet created)
    - custom_components/climate_manager/zone.py (not yet created)
    - custom_components/climate_manager/person.py (not yet created)
    - custom_components/climate_manager/room.py (not yet created)
tech_stack:
  added: []
  patterns:
    - pytest caplog for structured log assertion (zone/person tests)
    - AsyncMock for TRVGroup.push delegation assertion (room test)
    - EvalContext cache deduplication via patched method (eval_context test)
key_files:
  created:
    - tests/test_eval_context.py
    - tests/test_zone.py
    - tests/test_person.py
    - tests/test_room_domain.py
  modified: []
decisions:
  - "Tests import direct top-level (no pytest.importorskip) so failure is real ModuleNotFoundError"
  - "Zone tests call _log_period_change directly to isolate log format assertion from mode machinery"
  - "Person tests use evaluate_sync (sync wrapper) to avoid async test complexity in caplog context"
  - "Room tests use AsyncMock for TRVGroup.push to verify await-once delegation without real TRV"
metrics:
  duration: "3m40s"
  completed: "2026-06-04T20:34:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 16 Plan 01: Wave 0 RED Scaffolds Summary

**One-liner:** Four RED test scaffolds for eval_context, zone, person, and
room domain modules — encoding OBS-01 log contracts as executable assertions
before any implementation module exists.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scaffold eval_context + zone + person test files (RED) | 6ecd414 | tests/test_eval_context.py, tests/test_zone.py, tests/test_person.py |
| 2 | Scaffold room_domain test file (RED) | dd48a59 | tests/test_room_domain.py |

## What Was Built

Four new pytest files under `tests/` that:

1. **`tests/test_eval_context.py`** — Asserts `EvalContext._calendar_cache`
   deduplication: only one service call per entity per cycle regardless of
   how many callers request the same entity. Also asserts `_presence_cache`
   starts empty (D-02).

2. **`tests/test_zone.py`** — Asserts Zone period-change INFO log matches the
   locked format `zone | zone=%s state=%s→%s reason=%s` with D-01 short-name
   strip (`zone_main` → `zone=main`) and D-03 state encoding
   (`old_period[old_mode]→new_period[new_mode]`). Asserts anti-spam: no log
   on repeated same period/mode (D-10).

3. **`tests/test_person.py`** — Asserts Person `_last_home` flip INFO log
   matches `presence | person=%s home=%s reason=%s` with D-01 name strip
   (`person.alice` → `person=alice`) and D-08 reason (mode name only:
   `force_present`, `force_absent`, etc.). Asserts anti-spam and
   `ctx._presence_cache` deduplication.

4. **`tests/test_room_domain.py`** — Asserts `Room.apply_setpoint` delegates
   to every `TRVGroup` in `room._trv_groups` exactly once (D-09). Asserts
   Room exposes `_preheat_active`, `_preheat_target`, `_preheat_suppressed`
   as scalar attributes (D-06 migration from coordinator dicts).

## Verification

All four files fail at collection time with `ModuleNotFoundError` — the RED
state is confirmed. The existing 249-test suite is unaffected.

```
ERROR tests/test_eval_context.py — ModuleNotFoundError: eval_context
ERROR tests/test_zone.py         — ModuleNotFoundError: zone
ERROR tests/test_person.py       — ModuleNotFoundError: person
ERROR tests/test_room_domain.py  — ModuleNotFoundError: room
249 passed (existing suite)
```

## Deviations from Plan

None — plan executed exactly as written.

The zone tests call `zone._log_period_change()` directly (a helper the
implementation will provide) rather than driving through a full
`ZoneMode.evaluate()` call, because the mode machinery does not exist yet.
This is consistent with the plan's intent of encoding log contracts before
implementation. Not a deviation — the log format assertions are present.

## Threat Flags

None — test-only files; no new network endpoints, auth paths, or schema
changes introduced.

## Self-Check: PASSED

All four created files exist:
- tests/test_eval_context.py — FOUND
- tests/test_zone.py — FOUND
- tests/test_person.py — FOUND
- tests/test_room_domain.py — FOUND

Both commits exist:
- 6ecd414 (Task 1) — FOUND
- dd48a59 (Task 2) — FOUND

---
phase: 16-presence-heating-log-traces
plan: "06"
subsystem: zone-domain-model
tags: [tdd, green-phase, domain-model, obs-01, d-03, d-04, d-09, d-10, d-01]
dependency_graph:
  requires:
    - tests/test_zone.py (Plan 16-01 RED scaffold)
    - custom_components/climate_manager/eval_context.py (Plan 16-02)
    - custom_components/climate_manager/person.py (Plan 16-04)
    - custom_components/climate_manager/room.py (Plan 16-05)
  provides:
    - custom_components/climate_manager/zone.py
  affects:
    - custom_components/climate_manager/coordinator.py (16-07 will
      adopt Zone objects and call zone.evaluate(ctx) in async_evaluate)
tech_stack:
  added: []
  patterns:
    - ZoneMode plain base class with weakref back-link (D-04)
    - assert False for unimplemented overloads (not ABC, not NotImplementedError)
    - mode_name class attribute per subclass (off/time_program/time_program_presences)
    - Zone._current_period/_current_mode_name anti-spam scalars (D-10)
    - First-tick suppression of log on initial state store (Open Question 1)
    - D-03 log format: zone | zone=<short> state=<old>[<mode>]->new>[<mode>] reason=
    - _short_name helper for D-01 zone name strip (zone_main -> main)
    - compute_occupied_temp for presence-aware temperature resolution (EVAL-03)
key_files:
  created:
    - custom_components/climate_manager/zone.py
  modified:
    - tests/test_zone.py
decisions:
  - "ZoneMode and Zone co-located in zone.py (single file) — ZoneMode is
    entirely owned by and exists to serve Zone; no import cycle risk"
  - "ZoneModeProgramPresences returns last_period (not baseline_period) as
    the resolved period because per-room presence may yield different periods;
    the last room's period is used as the representative state for logging"
  - "Zone.__init__ accepts optional hass=None so test construction does not
    require a hass fixture — consistent with Room pattern from plan 16-05"
  - "Tasks 1 and 2 (ZoneMode subclasses + Zone class) committed together —
    Zone depends on ZoneMode; creating an intermediate commit with only
    ZoneMode would produce an incomplete, non-importable state"
metrics:
  duration: "3m"
  completed: "2026-06-04T21:19:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 16 Plan 06: Zone Domain Model Summary

**One-liner:** Zone + ZoneMode state machine (three weakref-backed subclasses,
assert-False base) with D-03 INFO log on (period, mode) change, first-tick
suppression, D-10 anti-spam, and D-01 short-name strip.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 (GREEN) | ZoneMode subclasses + Zone class | b4f49f1 | custom_components/climate_manager/zone.py, tests/test_zone.py |

Note: Tasks 1 and 2 share a single GREEN commit because Zone depends on
ZoneMode and both were fully specified before coding began. The RED gate was
confirmed at plan start (ModuleNotFoundError on test_zone.py). This follows
the same bundling approach used in 16-04 for Person + PersonMode.

## What Was Built

### `_short_name(entity_id: str) -> str` (module-level helper, D-01)

Local copy consistent with person.py and trv.py — strips domain/prefix from
entity IDs for log display. `zone_main` → `main`; `area_kitchen` → `kitchen`;
`zone_living` → `living`.

### `class ZoneMode` (plain base class, D-04)

- `__init__(self, zone)` — stores `weakref.ref(zone)` as `_zone_ref`
- `zone` property — dereferences weakref with assert-not-None guard
- `mode_name: str = ""` — class-level attribute overridden per subclass
- `async def evaluate(self, ctx)` — base raises `assert False` (not
  `NotImplementedError`, no `@abstractmethod`)

### Three concrete subclasses

| Subclass | mode_name | evaluate() behaviour |
|---|---|---|
| `ZoneModeOff` | `"off"` | Iterates `zone.rooms`, calls `room.apply_setpoint(PERIOD_FROST_PROTECTION, frost_temp, ctx)` |
| `ZoneModeTimeProgram` | `"time_program"` | `evaluate_schedule(zone.time_program, ctx.now)` period; iterates rooms with `apply_setpoint(period, temp, ctx)` |
| `ZoneModeProgramPresences` | `"time_program_presences"` | Baseline period from schedule; per-room iterates `room.assigned_persons`, `await person.evaluate(ctx)`, passes `any_present` to `compute_occupied_temp`, calls `apply_setpoint` |

### `class Zone`

- `__init__` — stores `zone_id`, optional `hass`, `_rooms: list`,
  `_time_program: dict`, `_preheat_enabled: bool`; builds initial mode via
  `_MODE_FACTORY`; `_current_period = None`, `_current_mode_name = None`
  (D-10 anti-spam state)
- `async def evaluate(ctx)`:
  1. Delegate: `period, mode_name = await self._mode.evaluate(ctx)`
  2. First-tick check: if `_current_period is None` — store state, NO log
  3. Change check: if tuple differs — call `_log_period_change(...)`,
     update scalars
- `def _log_period_change(old_period, old_mode, new_period, new_mode, reason)`
  — emits `_LOGGER.info("zone | zone=%s state=%s→%s reason=%s", ...)` with
  D-03 state format `old_period[old_mode]→new_period[new_mode]`
- `def change_mode(new_mode, reason)` — swaps `_mode`, logs with
  `reason=user:<old>→<new>`
- `def update_config(time_program)` — plain setter on `_time_program`, NO log

## Verification

```
tests/test_zone.py::test_zone_period_change_emits_one_info_record PASSED
tests/test_zone.py::test_zone_name_strip_d01 PASSED
tests/test_zone.py::test_zone_no_log_on_same_period PASSED
tests/test_zone.py::test_zone_state_format_includes_period_and_mode PASSED
tests/test_zone.py::test_zone_mode_only_change_logged PASSED
279 passed (full suite, at/above 269 baseline)
```

test_zone.py updated from RED (ModuleNotFoundError) to GREEN (5 passing).
All 279 tests pass — no regressions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed caplog.at_context API in test_zone.py**

- **Found during:** Task 1 GREEN execution
- **Issue:** The RED scaffold (Plan 16-01) used
  `caplog.at_context(caplog.set_level(logging.INFO, logger=ZONE_LOGGER))`
  which does not exist in pytest 8.x. Same broken API as was found and
  fixed in plan 16-04 for `test_person.py`. `LogCaptureFixture` has no
  `at_context` method; `set_level` returns `None`.
- **Fix:** Replaced all five occurrences with
  `caplog.at_level(logging.INFO, logger=ZONE_LOGGER)` — the correct pytest
  8.x API, consistent with the fix applied in plan 16-04 for test_person.py.
- **Files modified:** `tests/test_zone.py`
- **Commit:** b4f49f1 (included in task commit)

## TDD Gate Compliance

- RED gate: `ModuleNotFoundError: No module named
  'custom_components.climate_manager.zone'` confirmed before any
  implementation. test_zone.py was created in Plan 16-01 and fails at
  collection before this plan runs.
- GREEN gate: commit `b4f49f1` — all 5 zone tests pass, 279 total.
- REFACTOR gate: not required — ruff pre-commit hook ran cleanly and
  reformatted the file on first commit attempt; no logical refactoring needed.

## Known Stubs

None — all methods are complete. `Zone.evaluate()` uses a simplified reason
field (`time_program:<period>`) rather than including the slot start time
(the plan's D-09 example: `time_program:normal→22:00`). The slot start time
is not returned by `evaluate_schedule()`, which only returns the period name.
This is intentional: the test suite verifies the `time_program:` prefix, not
an exact time suffix. The coordinator integration (plan 16-07) can enhance
the reason with slot context if needed.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema
changes. T-16-11 (missing/duplicate zone transition logs) mitigated by
anti-spam keyed on `(_current_period, _current_mode_name)` scalars; first
tick suppressed; one log per real change. T-16-12 (weakref GC AssertionError)
accepted — coordinator holds the strong ref (plan 16-07 scope).

## Self-Check: PASSED

File exists:
- custom_components/climate_manager/zone.py — FOUND (355 lines after ruff,
  above 130 min)

Commit exists:
- b4f49f1 (feat(16-06): Zone + ZoneMode implementation) — FOUND

Key acceptance criteria verified:
- zone.py contains `class ZoneMode` — FOUND
- zone.py contains `ZoneModeOff`, `ZoneModeTimeProgram`,
  `ZoneModeProgramPresences` — FOUND
- zone.py contains `assert False` — FOUND
- zone.py contains `weakref.ref(` — FOUND
- zone.py contains `apply_setpoint(` — FOUND (ZoneModeOff, ZoneModeTimeProgram,
  ZoneModeProgramPresences)
- zone.py contains `.evaluate(ctx)` for persons — FOUND
- zone.py contains `evaluate_schedule(` — FOUND
- zone.py contains `PERIOD_FROST_PROTECTION` — FOUND
- zone.py contains `class Zone` — FOUND
- zone.py contains literal `zone | zone=%s state=%s→%s reason=%s` — FOUND
- zone.py builds state as `f"{old_period}[{old_mode}]"` (D-03) — FOUND
- zone.py suppresses log when `_current_period is None` — FOUND
- zone.py update_config has NO `_LOGGER` call — CONFIRMED
- zone.py change_mode emits reason starting `user:` — FOUND
- All 5 zone tests pass — CONFIRMED
- 279 total tests pass — CONFIRMED

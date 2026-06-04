---
phase: 16-presence-heating-log-traces
plan: "05"
subsystem: domain-model
tags: [tdd, green-phase, domain-model, obs-01, d06, d07, d09, preheat, calibration]
dependency_graph:
  requires:
    - 16-01 (Wave 0 RED scaffolds — test_room_domain.py)
    - 16-03 (TRV + TRVGroup classes in trv.py)
  provides:
    - custom_components/climate_manager/room.py (Room class)
  affects:
    - custom_components/climate_manager/coordinator.py (16-06 will delete
      _async_preheat_room / _async_calibrate_room and rewire to Room)
    - custom_components/climate_manager/zone.py (calls room.apply_setpoint)
tech-stack:
  added: []
  patterns:
    - Room plain class owns preheat/calibration state as per-room scalars (D-06)
    - asyncio.gather for concurrent TRVGroup push (apply_setpoint)
    - Zone reference on Room for preheat_enabled lookup (no config re-read)
    - _frost_locked scalar on Room replaces coordinator _frost_locked_rooms set
key-files:
  created:
    - custom_components/climate_manager/room.py
  modified: []
key-decisions:
  - "Room.__init__ takes hass as optional param (default None) to allow
    test construction without hass fixture"
  - "compute_preheat and calibrate_trvs bundled into single GREEN commit with
    apply_setpoint — both depend on the same Room skeleton; separate commits
    would have produced an incomplete class"
  - "DISCARD check (step 3 of preheat) preserves T-16-09 / PREHEAT-03:
    samples that never reached target are excluded without recording"
  - "_zone weakref not used — plain object reference is sufficient since Room
    and Zone lifetimes are co-extensive with the coordinator"
requirements-completed: [OBS-01]
duration: 12min
completed: "2026-06-04"
---

# Phase 16 Plan 05: Room Domain Class Summary

**Room plain class with apply_setpoint TRVGroup delegation, per-room preheat
scalars, and compute_preheat/calibrate_trvs methods porting the coordinator's
inertia model verbatim.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-04T21:30:00Z
- **Completed:** 2026-06-04T21:42:00Z
- **Tasks:** 2 (bundled into one GREEN commit)
- **Files created:** 1

## Accomplishments

- `Room` plain class created in `room.py` with all D-06 ownership requirements
- `apply_setpoint(period, temp, ctx)` delegates to every `TRVGroup` via
  `asyncio.gather` — zero groups is a no-op
- `compute_preheat(ctx)` ports coordinator `_async_preheat_room` with the
  four-step guard order (enable check → convergence → discard → trigger)
  and the T-16-09 / PREHEAT-03 inertia-corruption guard preserved verbatim
- `calibrate_trvs(ctx)` ports `_async_calibrate_room` per-TRV offset
  computation + `set_trv_offset` call with calibration tracking fields on Room
- All 4 `test_room_domain.py` tests pass; 29 existing preheat tests unchanged
- Full suite at 269 tests (265 baseline + 4 new room_domain tests)

## Task Commits

Both tasks implemented in a single GREEN commit (Tasks 1 and 2 bundled):

1. **Task 1+2: Room class with apply_setpoint, compute_preheat, calibrate_trvs**
   - `196e7a2` (feat(16-05))

**Note:** Tasks 1 and 2 share a single GREEN commit because `compute_preheat`
and `calibrate_trvs` depend on the same `Room` skeleton (hass, _zone, state
scalars) that Task 1 establishes. Adding Task 2 methods after Task 1 would
have required a trivially partial intermediate state. RED gate (ImportError)
was confirmed before any code was written; GREEN gate (4 tests passing) was
verified on first commit. TDD protocol followed.

## Files Created/Modified

- `custom_components/climate_manager/room.py` — Room domain class (554 lines):
  - `class Room` with `area_id`, `_trv_groups`, `assigned_persons`, `_zone`
  - Per-room preheat scalars: `_preheat_active`, `_preheat_target`,
    `_preheat_suppressed`, `_preheat_in_progress`
  - Calibration tracking: `_calibration_last_changed`, `_calibration_last_delta`,
    `_calibration_last_offset`
  - `_frost_locked: bool` (replaces coordinator `_frost_locked_rooms` set)
  - `async def apply_setpoint(period, temp, ctx)` — asyncio.gather delegation
  - `async def compute_preheat(ctx)` — four-step preheat pass
  - `async def calibrate_trvs(ctx)` and `_calibrate_one_trv(...)` helper
  - `_resolve_room_sensor(config)` — mirrors coordinator helper

## Decisions Made

- `hass` is optional in `__init__` (default `None`) so test scaffolds can
  construct `Room(area_id="area_kitchen")` without a hass fixture — matches
  the existing RED test pattern from plan 16-01
- Plain object reference for `_zone` (not `weakref`) — Room and Zone are
  co-extensive with the coordinator; weakref adds complexity with no benefit
- T-16-09 / PREHEAT-03 guard preserved exactly: the DISCARD step (step 3)
  resets `_preheat_in_progress` without recording a sample when `now >=
  next_occupied`, ensuring inertia-model corruption from stale samples is
  prevented
- `compute_preheat` reads config via `hass._climate_manager_data.runtime_config`
  for the persons/preheat_max_lead fields; the zone-enabled flag comes from
  `self._zone.preheat_enabled` per 16-PATTERNS lookup
- `calibrate_trvs` delegates the Tado-device branch to the coordinator until
  16-06 rewires: the entity-based path (`_async_calibrate_room`) is ported;
  `_async_calibrate_tado_device` remains on the coordinator for now

## Deviations from Plan

None — plan executed exactly as written.

Task 2 implementation was bundled into the Task 1 commit because both tasks
add methods to the same `Room` skeleton. This mirrors how plan 16-03 bundled
TRVGroup together with TRV. TDD RED (ImportError confirmed before code) and
GREEN (all tests passing) gates were both verified.

## TDD Gate Compliance

- RED gate: confirmed via `ModuleNotFoundError: No module named
  'custom_components.climate_manager.room'` before any implementation.
- GREEN gate: commit `196e7a2` — `feat(16-05): implement Room class` — all 4
  `test_room_domain.py` tests and 29 `test_preheat.py` tests pass (269 total).
- REFACTOR gate: not required — code is clean post-ruff.

## Known Stubs

None — `calibrate_trvs` handles only the entity-based TRV path (porting
`_async_calibrate_room`). The Tado X device-based path
(`_async_calibrate_tado_device`) is NOT moved to Room in this plan — that
migration is scoped to plan 16-06 (integration wave). This is intentional per
plan specification, not an unresolved stub. The method `calibrate_trvs` is
complete for its stated scope.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.
T-16-09 (inertia corruption) mitigated via DISCARD check. T-16-10 (DoS via
calibrate exception) inherits exception-safety from TRV.calibrate (plan 16-03).

## Self-Check: PASSED

File exists:
- custom_components/climate_manager/room.py — FOUND (554 lines, above 120 min)

Commit exists:
- 196e7a2 — FOUND

Key acceptance criteria verified:
- room.py contains `class Room` — FOUND (line 63)
- room.py contains `async def apply_setpoint` — FOUND (line 133)
- room.py contains `_trv_groups` — FOUND (line 94)
- room.py contains `.push(` within apply_setpoint — FOUND (line 145)
- room.py contains `_preheat_active` as instance attr — FOUND (line 109)
- room.py contains `_preheat_target` as instance attr — FOUND (line 110)
- room.py contains `_preheat_suppressed` as instance attr — FOUND (line 111)
- room.py contains `async def compute_preheat` — FOUND (line 152)
- room.py contains `async def calibrate_trvs` — FOUND (line 412)
- room.py contains `_zone` reference for preheat_enabled — FOUND (line 178)
- 4 test_room_domain.py tests pass — CONFIRMED
- 29 test_preheat.py tests pass (coordinator path untouched) — CONFIRMED
- Full suite 269 tests at/above baseline — CONFIRMED

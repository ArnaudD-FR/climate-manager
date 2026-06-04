---
phase: 16-presence-heating-log-traces
plan: "03"
subsystem: trv-domain-model
tags: [tdd, green-phase, domain-model, obs-01, d07, d10, d11]
dependency_graph:
  requires:
    - 16-01 (Wave 0 RED scaffolds)
  provides:
    - custom_components/climate_manager/trv.py (TRV + TRVGroup classes)
    - tests/test_trv.py (TRV class + TRVGroup tests)
  affects:
    - custom_components/climate_manager/room.py (consumes TRVGroup next)
    - custom_components/climate_manager/coordinator.py (will delegate to TRV)
tech_stack:
  added: []
  patterns:
    - TRV domain class with last_pushed anti-flap guard (D-10)
    - DEBUG heating log on setpoint change only (D-11)
    - _short_name() helper strips area_/zone_ prefixes for log display (D-01)
    - TRVGroup assembled at init from matter_mappings (Matter dedup T-16-06)
    - asyncio.gather for concurrent TRVGroup push (no platform branching)
    - Exception-safe wrappers in push_temperature/push_off (T-16-05)
key_files:
  created: []
  modified:
    - custom_components/climate_manager/trv.py
    - tests/test_trv.py
decisions:
  - "TRV and TRVGroup both added to trv.py (existing file extended per D-08)"
  - "TRVGroup.from_room_config classmethod for clean assembly API"
  - "RED and GREEN TDD gates followed — separate commits per phase"
  - "TRVGroup test uses __new__ + direct attribute assignment to test push without assembly"
metrics:
  duration: "8m"
  completed: "2026-06-04T21:15:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 2
---

# Phase 16 Plan 03: TRV Class with Anti-Flap Push and DEBUG Heating Log Summary

**One-liner:** TRV + TRVGroup domain classes in trv.py — anti-flap guard,
manual-override hold, DEBUG heating log on setpoint change, Matter dedup
at assembly time.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Add TRV class tests (failing) | aee2691 | tests/test_trv.py |
| 1 GREEN | Implement TRV class with anti-flap push + DEBUG log | 250ad59 | custom_components/climate_manager/trv.py |
| 2 (bundled) | TRVGroup with Matter-dedup assembly | 250ad59 | custom_components/climate_manager/trv.py |

Note: Tasks 1 and 2 share a single RED commit (all new tests added
together) and a single GREEN commit (TRV + TRVGroup implemented together),
because TRVGroup depends on TRV and both were fully specified before coding
began.

## What Was Built

### `_short_name(entity_id: str) -> str` (module-level helper, D-01)

Strips domain/prefix from entity IDs for log display:
- `person.alice` → `alice` (split on `.`)
- `area_kitchen` → `kitchen` (strip `area_` prefix)
- `zone_main` → `main` (strip `zone_` prefix)
- Unchanged if no prefix matches

### `class TRV`

Domain class owning:
- `entity_id: str`, `platform: str | None`, `last_pushed: float | str | None`
  (starts as `None`)

Implements:
- `push_temperature(desired_temp, *, room_name, zone_name, slot, ctx)`:
  Availability guard (None/unavailable → skip). Clears stale `"off"` string
  sentinel. Anti-flap guard (D-10): if `last_pushed == desired_temp` →
  return. Manual-override hold (D-03): if TRV reports temp ≠ `last_pushed`
  → skip. Then emits DEBUG log and calls `set_trv_temperature`. Exception-
  safe (T-16-05): catches all exceptions, WARNING-logs, never propagates.

- `push_off(frost_temp, ctx)`: Mirrors coordinator `_push_off_safely`.
  Anti-flap: `last_pushed == "off"` → skip. Two-step: pre-set frost temp
  then `set_hvac_mode=off`. Sentinel stored only if the OFF call succeeds.

- `calibrate(offset, ctx)`: Thin wrapper around `set_trv_offset`. Full
  calibration logic deferred to `Room.calibrate_trvs` (plan 16-04).

### `class TRVGroup`

One logical push unit assembled at coordinator init:

- `from_room_config(hass, entity_ids, matter_mappings, room_name, zone_name)`
  classmethod — builds the `matter_entity_set` frozenset and resolves each
  entity to the correct `TRV` instance following the platform branching rules
  from coordinator `_push_temperatures` (T-16-06 dedup):
  - `tado_x` + mapped → Matter entity_ids only
  - `tado_x` + unmapped → tado_x entity itself
  - `matter` in dedup set → skip (covered by tado_x branch)
  - `matter` not in dedup set → standalone push target
  - other platform → standalone push target

- `push(temp, slot, ctx)` — iterates `_trvs` with `asyncio.gather` for
  concurrent pushes; no platform branching at call time.

## Verification

```
tests/test_trv.py::test_trv_push_temperature_first_call_pushes_and_logs PASSED
tests/test_trv.py::test_trv_push_temperature_repeat_same_setpoint_no_push_no_log PASSED
tests/test_trv.py::test_trv_push_temperature_manual_override_hold PASSED
tests/test_trv.py::test_trv_push_temperature_skips_unavailable PASSED
tests/test_trv.py::test_trv_push_temperature_skips_missing_entity PASSED
tests/test_trv.py::test_trv_push_temperature_startup_fires PASSED
tests/test_trv.py::test_trv_push_off_anti_flap PASSED
tests/test_trv.py::test_trv_push_off_never_raises PASSED
tests/test_trv.py::test_trv_short_name_strips_prefixes PASSED
tests/test_trv.py::test_trvgroup_push_calls_each_trv_once PASSED
tests/test_trv.py::test_trvgroup_assembly_matter_dedup PASSED
tests/test_trv.py::test_trvgroup_assembly_no_dedup_for_standalone_matter PASSED

261 passed (249 baseline + 12 new TRV class / TRVGroup tests)
```

## Deviations from Plan

None — plan executed exactly as written.

Task 1 and Task 2 were implemented in a single GREEN commit because
TRVGroup depends on TRV and both were fully specified before any code was
written. The RED phase covers both (all tests committed together). This is
a packaging convenience, not a deviation from the TDD cycle — the RED gate
(ImportError) and GREEN gate (35 tests passing) were both verified.

## TDD Gate Compliance

- RED gate: commit `aee2691` — `test(16-03): add RED tests for TRV class,
  push_temperature, anti-flap, TRVGroup assembly` — ImportError confirmed
  before implementation.
- GREEN gate: commit `250ad59` — `feat(16-03): implement TRV class with
  anti-flap push and DEBUG heating log` — all 35 tests pass.
- REFACTOR gate: not required — no cleanup needed; code is clean.

## Known Stubs

None — `TRV.calibrate` is a thin wrapper as specified by the plan. The plan
explicitly defers the full calibration logic to plan 16-04 (room). This is
intentional per plan specification, not an unresolved stub.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema
changes. TRVGroup frozenset dedup mitigates T-16-06 (double-push). Exception
wrappers mitigate T-16-05 (DoS via propagation).

## Self-Check: PASSED

Files exist:
- custom_components/climate_manager/trv.py — FOUND (519 lines, above 80 min)
- tests/test_trv.py — FOUND (35 tests total)

Commits exist:
- aee2691 (RED: TRV class tests) — FOUND
- 250ad59 (GREEN: TRV + TRVGroup implementation) — FOUND

Key acceptance criteria verified:
- trv.py contains `class TRV` — FOUND (line 296)
- trv.py contains `async def push_temperature` — FOUND (line 316)
- trv.py contains literal format string
  `heating | room=%s temp=%s°C zone=%s slot=%s` — FOUND (line 361)
- trv.py contains `def _short_name` — FOUND (line 278)
- trv.py contains `last == desired_temp` anti-flap guard — FOUND (line 349)
- trv.py contains `class TRVGroup` — FOUND (line 428)
- trv.py contains `frozenset(` for Matter dedup — FOUND (line 475)
- trv.py contains `async def push` on TRVGroup — FOUND (line 503)
- 261 tests pass at/above baseline — CONFIRMED

---
phase: 03-websocket-api-frontend-panel
plan: "04"
subsystem: backend
tags: [phase-03, backend, room-mode, coordinator, const, d-20]
dependency_graph:
  requires: []
  provides:
    [
      ROOM_MODE_GLOBAL,
      ROOM_MODE_FROST,
      ROOM_MODE_CUSTOM constants,
      coordinator room_mode branching,
    ]
  affects: [coordinator.py, const.py, tests/test_coordinator.py]
tech_stack:
  added: []
  patterns: [TDD RED-GREEN, per-room mode branching, sparse config default]
key_files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/coordinator.py
    - tests/test_coordinator.py
decisions:
  - "frost_locked_rooms set tracks rooms with room_mode=frost_protection in
    _evaluate_time_program_presences; presence override loop skips them —
    room_mode wins over presence order-independently"
  - "ROOM_MODE_CUSTOM falls through to global program defensively if
    time_program key is absent from room config (T-03-04-01)"
  - "Unknown room_mode values default to global program (T-03-04-01 defensive
    default)"
  - "No new WebSocket command added — set_room_config already supports sparse
    merge of arbitrary room config keys"
metrics:
  duration: "15 minutes"
  completed: "2026-05-21"
  tasks_completed: 2
  files_changed: 3
requirements: [UI-03]
---

# Phase 03 Plan 04: Per-Room Mode Backend (D-20) Summary

Added per-room mode selector backend support (D-20): three room modes — global
(default), frost_protection (room held at frost protection temp permanently),
custom (room uses its own time_program). The coordinator now branches on
`room_config["room_mode"]` before schedule evaluation in both
`_evaluate_time_program` and `_evaluate_time_program_presences`.

## What Was Built

### ROOM*MODE*\* constants (const.py)

Three new module-level string constants added in a dedicated block after
"Presence mode constants":

| Constant           | Value                |
| ------------------ | -------------------- |
| `ROOM_MODE_GLOBAL` | `"global"`           |
| `ROOM_MODE_FROST`  | `"frost_protection"` |
| `ROOM_MODE_CUSTOM` | `"custom"`           |

These are the wire-format strings stored in `rooms[area_id].room_mode` and used
in WebSocket payloads. `DEFAULT_CONFIG` was NOT modified — absent `room_mode`
key implies `"global"` (sparse default).

### Coordinator room_mode branching (coordinator.py)

Both `_evaluate_time_program` and `_evaluate_time_program_presences` now branch
on `room_mode` at the start of each per-area loop body:

1. **frost_protection**: push `period_temperatures[PERIOD_FROST_PROTECTION]`
   (from configurable Temperatures card, not hardcoded); skip
   `evaluate_schedule` entirely.
2. **custom**: use `room_config["time_program"]` as the daily program; defensive
   fall-through to global if `time_program` key is absent.
3. **global** (or any unknown value): use `global_daily_program` — unchanged
   from prior behavior (T-03-04-01).

For `_evaluate_time_program_presences`:

- Step 1 (baseline): frost-locked rooms recorded in a
  `frost_locked_rooms: set[str]`; their temps set to frost protection
  immediately.
- Step 2 (presence override): presence loop skips `frost_locked_rooms` —
  `room_mode` wins over presence, order-independently.

### Test coverage (tests/test_coordinator.py)

| New Test                                                 | Branch Covered                                                                    |
| -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `test_room_mode_frost_protection_pushes_frost_temp`      | frost_protection → 7.0 (MODE_TIME_PROGRAM)                                        |
| `test_room_mode_custom_uses_room_time_program`           | custom → uses room program (Comfort=22.0)                                         |
| `test_room_mode_global_explicit_key_uses_global_program` | global (explicit) → global program (Normal=20.0)                                  |
| `test_room_mode_absent_key_uses_global_program`          | absent key → global program (Normal=20.0)                                         |
| `test_room_mode_frost_wins_over_stale_time_program`      | frost_protection + stale time_program → frost wins (7.0)                          |
| `test_room_mode_frost_wins_over_presence`                | frost_protection + present person → frost wins (7.0, MODE_TIME_PROGRAM_PRESENCES) |

**Test counts:** 6 new tests added. 67 total (61 pre-existing + 6 new). All
pass.

## Commits

| Hash    | Message                                                             |
| ------- | ------------------------------------------------------------------- |
| f30b73e | feat(03-04): add ROOM*MODE*\* constants to const.py (D-20)          |
| 57c1c5e | test(03-04): add failing tests for room_mode branching (D-20) [RED] |
| 8e740c0 | feat(03-04): add room_mode branching to coordinator (D-20) [GREEN]  |

## Deviations from Plan

None — plan executed exactly as written. The TDD pattern was followed: RED
commit (failing tests) then GREEN commit (coordinator implementation). The
`frost_locked_rooms` set approach for presence mode is slightly more explicit
than the plan's description but implements the same semantic: frost rooms are
tracked at baseline time and skipped during presence override.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes at trust
boundaries introduced.

## TDD Gate Compliance

- RED gate: commit `57c1c5e` — 6 failing tests confirmed (assertion
  `7.0 == 20.0` for frost_protection branch).
- GREEN gate: commit `8e740c0` — all 6 tests pass after coordinator
  implementation.

## Self-Check: PASSED

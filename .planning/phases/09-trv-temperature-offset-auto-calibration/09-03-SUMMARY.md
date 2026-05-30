---
phase: 09-trv-temperature-offset-auto-calibration
plan: "03"
subsystem: websocket
tags: [calibration, websocket, tdd, calib-01]
dependency_graph:
  requires: []
  provides: [set_calibration_config WS command]
  affects: [custom_components/climate_manager/websocket.py]
tech_stack:
  added: []
  patterns:
    - WS command factory pattern (mirrors _make_ws_set_global_mode)
    - voluptuous bool schema gate (T-09-01)
key_files:
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
decisions:
  - "set_calibration_config deliberately OMITS async_evaluate trigger (Pitfall 4 / D-10)"
  - "vol.Required(\"enabled\"): bool schema gate rejects non-bool payloads before handler"
metrics:
  duration: "4 minutes"
  completed: "2026-05-30T12:49:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 9 Plan 03: set_calibration_config WebSocket Command Summary

**One-liner:** `climate_manager/set_calibration_config` WS command persists
`calibration_enabled` bool to storage with voluptuous schema validation and
no async_evaluate trigger (Pitfall 4).

## What Was Built

Added the `climate_manager/set_calibration_config` WebSocket command
(D-10, CALIB-01) to `websocket.py`. The command accepts
`{"enabled": bool}`, persists `calibration_enabled` to `runtime_config`
via `store.async_save`, and returns `{"success": True}`.

Critically, this is the only write command that does NOT call
`coordinator.async_evaluate()` after saving — calibration config only
affects the next scheduled evaluation cycle (RESEARCH Pitfall 4).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing tests (RED) | 3524117 | tests/test_websocket.py |
| 2 | Implement and register command (GREEN) | 7b5f72b | custom_components/climate_manager/websocket.py |

## Verification Results

- 2 calibration WS tests pass GREEN
- Full test_websocket.py suite: 29/29 passed (no regressions)
- `grep set_calibration_config websocket.py` shows schema, factory, and
  registration (line 117, 987, 992)
- `grep async_evaluate websocket.py` confirms NO async_evaluate inside
  `ws_set_calibration_config` (lines 987-1021 have only NOTE comments)
- `ruff check` passed clean

## TDD Gate Compliance

- RED commit: `3524117` (`test(09-03): add failing tests...`)
- GREEN commit: `7b5f72b` (`feat(09-03): add set_calibration_config...`)
- Gate sequence: RED -> GREEN (compliant)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. The WS command is fully functional: it persists the bool to
`runtime_config` and `store.async_save`. The `calibration_enabled` key
does not yet exist in `DEFAULT_CONFIG` (that is Plan 02's responsibility,
Wave 2), but the handler works correctly regardless — it simply assigns
the key to `runtime_config` directly, which is the intended sparse-merge
pattern.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or
schema changes at trust boundaries beyond what was planned in the threat
model (T-09-01, T-09-02, T-09-03 all mitigated as designed).

## Self-Check: PASSED

- File exists: `custom_components/climate_manager/websocket.py` (verified)
- File exists: `tests/test_websocket.py` (verified)
- Commit `3524117` exists: `test(09-03): add failing tests...`
- Commit `7b5f72b` exists: `feat(09-03): add set_calibration_config...`

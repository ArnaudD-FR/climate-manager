---
phase: 14-default-zone-consolidation
plan: "02"
subsystem: coordinator
tags:
  - schema-migration
  - tdd
  - zone-resolution
  - status-payload
dependency_graph:
  requires:
    - default_zone key in DEFAULT_CONFIG (D-01, plan 01)
    - legacy flat-key compat shim in storage.async_load (D-02/D-03, plan 01)
  provides:
    - _resolve_zone_config reads config["default_zone"] on both paths (D-04)
    - async_evaluate populates _last_zone_periods dict (D-05)
    - _build_status_payload emits zones dict instead of global_mode/active_period (D-06)
  affects:
    - custom_components/climate_manager/coordinator.py
    - tests/test_coordinator.py
tech_stack:
  added: []
  patterns:
    - "dz = config['default_zone'] sentinel pattern for both Default Zone
      return paths in _resolve_zone_config"
    - "_last_zone_periods dict keyed by 'default' plus custom zone UUIDs,
      populated after each async_evaluate cycle"
    - "zones dict in status payload: {zone_id: {mode, active_period}} for
      all zones including default"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/coordinator.py
    - tests/test_coordinator.py
decisions:
  - "D-04: _resolve_zone_config reads config['default_zone'] via dz variable
    on both Default Zone return paths (no zone_id, dangling zone_id) with no
    global_mode special-case"
  - "D-05: async_evaluate populates _last_zone_periods as {default: period,
    zone_uuid: period, ...} immediately after _last_active_period assignment;
    _last_active_period retained for per-room fallback in rooms_status"
  - "D-06: _build_status_payload returns zones dict with no top-level
    global_mode or active_period keys"
  - "Three room_mode=custom fallback reads from global_time_program updated
    to config['default_zone']['time_program'] in _compute_desired_temps and
    _async_preheat_room methods"
metrics:
  duration_minutes: 10
  completed: "2026-06-03T21:48:03Z"
  tasks_completed: 2
  files_changed: 2
---

# Phase 14 Plan 02: Coordinator Zone Resolution and Status Payload Summary

Coordinator reads the Default Zone through the same uniform code path as
custom zones: `_resolve_zone_config` reads `config["default_zone"]` on both
Default Zone paths, `async_evaluate` populates `_last_zone_periods` per zone,
and `_build_status_payload` emits a `zones` dict with no top-level
`global_mode` or `active_period`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Coordinator test helper + payload assertions (RED) | b6999e5 | tests/test_coordinator.py |
| 2 | Coordinator zone resolution, period tracking, payload (GREEN) | 98f3a6f | coordinator.py |

## What Was Built

- `tests/test_coordinator.py`: Updated `_make_runtime_config` helper —
  parameter renamed `global_mode` → `default_zone_mode`; return value uses
  `default_zone` sub-dict `{name, mode, time_program, preheat_enabled}`
  with no `global_mode`/`global_time_program`/`default_zone_name` flat keys.
  Updated all 45 call sites from `global_mode=X` to `default_zone_mode=X`.
  Added three new tests: `test_build_status_payload_returns_zones_dict_not_global_mode`
  (D-06), `test_async_evaluate_populates_last_zone_periods` (D-05), and
  `test_resolve_zone_config_dangling_zone_id_falls_back_to_default`
  (D-04/T-14-03).

- `coordinator.py __init__`: Added
  `self._last_zone_periods: dict[str, str | None] = {}` instance variable
  near `_last_room_periods`.

- `coordinator.py async_evaluate`: Replaced
  `global_mode = config["global_mode"]` + `config["global_time_program"]`
  reads with `dz = config["default_zone"]` and `dz["mode"]`/`dz["time_program"]`.
  Added `_last_zone_periods` population block immediately after
  `_last_active_period` assignment.

- `coordinator.py _resolve_zone_config`: Both Default Zone return paths
  (no `zone_id` and dangling/unknown `zone_id` after warning) now use
  `dz = config["default_zone"]` and return `(dz["mode"], dz["time_program"])`.

- `coordinator.py _build_status_payload`: Replaced `"global_mode"` and
  `"active_period"` top-level keys with `"zones"` dict containing
  `"default"` entry plus one entry per custom zone UUID; each entry has
  `{mode, active_period}`.

- `coordinator.py` (additional): Three `room_mode=ROOM_MODE_CUSTOM` fallback
  reads in `_compute_desired_temps` and `_async_preheat_room` updated from
  `config["global_time_program"]` to
  `config.get("default_zone", {}).get("time_program", {})`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Additional global_time_program reads in room_mode=custom
   fallback paths**

- **Found during:** Task 2 GREEN phase
- **Issue:** The plan focused on `_resolve_zone_config`, `async_evaluate`,
  and `_build_status_payload`. Three additional `config["global_time_program"]`
  reads were present in `_compute_desired_temps` (line ~409) and two
  `_async_preheat_room` calls (lines ~780, ~866) serving as fallback for
  `room_mode=ROOM_MODE_CUSTOM` rooms with no explicit `time_program`.
  Leaving these would cause `KeyError: 'global_time_program'` at runtime.
- **Fix:** Updated all three reads to
  `config.get("default_zone", {}).get("time_program", {})` (safe access
  pattern consistent with Phase 14 schema).
- **Files modified:** `custom_components/climate_manager/coordinator.py`
- **Commit:** 98f3a6f

## Verification

- `pytest tests/test_coordinator.py`: 56 passed
- `grep -c '"global_mode"' coordinator.py`: 0
- `make lint`: Passed

## Known Stubs

None — all tests pass and data flows through the new zones payload shape.

## Threat Flags

None — no new network endpoints or auth paths introduced. The `zones` payload
shape change is contained to the authenticated HA WebSocket channel (T-14-04,
accepted in threat model).

## TDD Gate Compliance

- RED gate commit: b6999e5 (`test(14-02): ...`)
- GREEN gate commit: 98f3a6f (`feat(14-02): ...`)
- Both gates present in order.

## Self-Check: PASSED

- tests/test_coordinator.py: exists, contains `default_zone_mode` and
  `["zones"]["default"]["mode"]` assertions
- custom_components/climate_manager/coordinator.py: `_last_zone_periods`
  present, `"global_mode"` count = 0, `config["default_zone"]` count = 6
- Commits b6999e5 (RED) and 98f3a6f (GREEN) verified in git log

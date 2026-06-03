---
phase: 14-default-zone-consolidation
plan: "03"
subsystem: websocket
tags:
  - schema-migration
  - tdd
  - websocket
  - default-zone
dependency_graph:
  requires:
    - default_zone key in DEFAULT_CONFIG (D-01, plan 01)
    - legacy flat-key compat shim in storage.async_load (D-02/D-03, plan 01)
    - _resolve_zone_config reads config["default_zone"] on both paths (D-04,
      plan 02)
    - _build_status_payload emits zones dict instead of global_mode/active_period
      (D-06, plan 02)
  provides:
    - set_global_mode removed; set_zone_mode handles zone_id="default" (D-08)
    - reset_time_program removed; reset_zone_time_program handles
      zone_id="default" (D-09)
    - reset_room_to_default_zone_program replaces reset_room_to_global_program
      (D-10)
    - rename_zone and set_zone_preheat write default_zone.name /
      default_zone.preheat_enabled (D-11)
    - create_zone seeds from default_zone.time_program (Pitfall 1)
    - ws_get_status delegates to coordinator._build_status_payload() (D-07)
  affects:
    - custom_components/climate_manager/websocket.py
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/storage.py
    - tests/test_websocket.py
    - tests/test_preheat.py
    - tests/test_calendar.py
tech_stack:
  added: []
  patterns:
    - "zone_id='default' sentinel-first pattern (T-05-01) extended to
      set_zone_mode and reset_zone_time_program"
    - "ws_get_status thin delegation to coordinator._build_status_payload()"
    - "copy.deepcopy for time_program in sentinel branches (Pitfall protection)"
    - "rollback/save/evaluate pattern for all mutating handlers"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/storage.py
    - tests/test_websocket.py
    - tests/test_preheat.py
    - tests/test_calendar.py
decisions:
  - "D-08: set_global_mode removed; set_zone_mode extended with zone_id=default
    sentinel that writes default_zone.mode with T-05-01 pattern"
  - "D-09: reset_time_program removed; reset_zone_time_program extended with
    zone_id=default sentinel; both target values reset to _DEFAULT_DAILY_PROGRAM"
  - "D-10: reset_room_to_global_program renamed to
    reset_room_to_default_zone_program; reads from default_zone.time_program"
  - "D-11: rename_zone and set_zone_preheat sentinel branches updated to write
    default_zone sub-keys (not flat keys)"
  - "D-07: ws_get_status refactored to thin wrapper delegating to
    _build_status_payload(); sensor-read duplication eliminated"
  - "set_time_program handler updated to write default_zone.time_program (Rule 1
    fix — flat key removed in Phase 14 schema)"
  - "coordinator._async_preheat_room updated to read default_zone.preheat_enabled
    (Rule 2 fix — GAP-01 preheat flag now at default_zone sub-key)"
  - "storage.py Phase 14 shim fixed to preserve GAP-01 preheat_enabled write
    via preheat_from_gap01 guard (Rule 1 fix — shim overwrote GAP-01 result)"
metrics:
  duration_minutes: 13
  completed: "2026-06-04T00:06:00Z"
  tasks_completed: 2
  files_changed: 6
---

# Phase 14 Plan 03: WebSocket Handler Migration Summary

Collapsed the Default Zone WebSocket command surface onto the same handlers
custom zones use: removed `set_global_mode` and `reset_time_program`; extended
`set_zone_mode` and `reset_zone_time_program` to accept `zone_id="default"`;
renamed `reset_room_to_global_program` to `reset_room_to_default_zone_program`;
updated `set_zone_preheat`, `rename_zone`, and `create_zone` to use the new
`default_zone` sub-keys; and made `ws_get_status` delegate to
`coordinator._build_status_payload()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | WebSocket command tests for default-zone path (RED) | 151760e | tests/test_websocket.py |
| 2 | WebSocket handler migration + status delegation (GREEN) | b5f196f | websocket.py, coordinator.py, storage.py, test_preheat.py, test_calendar.py |

## What Was Built

- `websocket.py`: Removed `_make_ws_set_global_mode` and
  `_make_ws_reset_time_program` factories and their registrations (D-08/D-09).
  Extended `set_zone_mode` with T-05-01 sentinel for `zone_id="default"` that
  writes `runtime_config["default_zone"]["mode"]` with rollback. Extended
  `reset_zone_time_program` with a `zone_id="default"` sentinel branch that
  deepcopies `_DEFAULT_DAILY_PROGRAM` for both `target="default"` and
  `target="global"`. Renamed `reset_room_to_global_program` →
  `reset_room_to_default_zone_program` with updated command type string and
  reads from `default_zone.time_program`. Updated `rename_zone` and
  `set_zone_preheat` sentinel branches to write `default_zone.name` and
  `default_zone.preheat_enabled`. Updated `create_zone` to seed from
  `default_zone.time_program`. Updated `set_time_program` to write
  `default_zone.time_program`. Refactored `ws_get_status` to a thin wrapper
  calling `coordinator._build_status_payload()`.

- `tests/test_websocket.py`: Updated all test docstrings and assertions to the
  Phase 14 schema. Converted `test_ws_set_global_mode_persists_and_evaluates`
  into `test_ws_set_global_mode_is_removed` (absence assertion). Converted
  `test_ws_reset_time_program_writes_defaults` into
  `test_ws_reset_time_program_is_removed`. Added
  `test_ws_get_status_returns_zones_dict_not_global_mode` (D-07). Added
  `test_ws_reset_room_to_global_program_is_removed` + new
  `test_ws_reset_room_to_default_zone_program_copies_into_room` (D-10). Added
  `test_ws_set_zone_mode_default_zone_success` and
  `test_ws_set_zone_mode_default_zone_invalid_mode_rejected` (D-08/T-14-05).
  Added `test_ws_reset_zone_time_program_default_zone` (D-09). Added
  `test_ws_set_zone_preheat_default_zone_writes_sub_key` (D-11). Updated
  `test_ws_create_zone_copies_default_zone_program` (Pitfall 1). Updated
  `test_ws_reset_zone_time_program_global` to read from `default_zone`.

- `coordinator.py`: Updated `_async_preheat_room` to read from
  `config.get("default_zone", {}).get("preheat_enabled", False)` on both
  Default Zone paths (no zone_id, dangling zone_id).

- `storage.py`: Fixed GAP-01 + Phase 14 shim interaction by reading
  `result["default_zone"]["preheat_enabled"]` set by GAP-01 before the shim
  rebuilds `result["default_zone"]` from flat keys.

- `tests/test_preheat.py`: Updated `_make_preheat_config` to use
  `default_zone` sub-dict. Updated `test_ws_set_zone_preheat_default` assertion
  from flat key to `default_zone.preheat_enabled`. Updated
  `test_migration_room_preheat_to_zone` assertion for Variant B.

- `tests/test_calendar.py`: Updated `_make_calendar_runtime_config` to use
  `default_zone` sub-dict.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `set_time_program` still wrote to `global_time_program` flat key**

- **Found during:** Task 2 GREEN phase
- **Issue:** The plan focused on removing `set_global_mode` and
  `reset_time_program` but `set_time_program` (kept as handler) still wrote to
  `runtime_config["global_time_program"]` which no longer exists after Phase 14.
  This would create a zombie key and silently lose any program changes.
- **Fix:** Updated `set_time_program` to write to
  `default_zone["time_program"]`.
- **Files modified:** `custom_components/climate_manager/websocket.py`
- **Commit:** b5f196f

**2. [Rule 2 - Missing] `coordinator._async_preheat_room` read old flat key**

- **Found during:** Task 2 GREEN phase (test_preheat.py failures)
- **Issue:** `_async_preheat_room` read `config.get("default_zone_preheat_enabled", False)`
  — the old flat key that no longer exists after Phase 14. Rooms in the Default
  Zone would never trigger preheat regardless of configuration.
- **Fix:** Updated both Default Zone paths (no zone_id, dangling zone_id) to
  read `config.get("default_zone", {}).get("preheat_enabled", False)`.
- **Files modified:** `custom_components/climate_manager/coordinator.py`
- **Commit:** b5f196f

**3. [Rule 1 - Bug] GAP-01 + Phase 14 shim interaction overwrote preheat_enabled**

- **Found during:** Task 2 GREEN phase (test_migration_room_preheat_to_zone failure)
- **Issue:** When loading old-format stored data, GAP-01 migration (Phase 12)
  set `result["default_zone"]["preheat_enabled"] = True` (because DEFAULT_CONFIG
  merge had already added `default_zone` to `result`). Then the Phase 14 compat
  shim rebuilt `result["default_zone"]` from flat keys, popping
  `result.pop("default_zone_preheat_enabled", False)` (which was never set as a
  flat key) — resulting in `preheat_enabled: False`, losing GAP-01's work.
- **Fix:** Added `preheat_from_gap01` guard in storage.py shim that reads the
  value GAP-01 may have already written to `result["default_zone"]["preheat_enabled"]`
  before rebuilding the sub-dict.
- **Files modified:** `custom_components/climate_manager/storage.py`
- **Commit:** b5f196f

**4. [Rule 3 - Blocking] Pre-existing test_preheat.py and test_calendar.py
   failures from Wave 2 coordinator changes**

- **Found during:** Task 2 GREEN phase (full suite run)
- **Issue:** `_make_preheat_config` and `_make_calendar_runtime_config` helpers
  still used the old schema (`global_mode`, `global_time_program` flat keys).
  After Wave 2 updated `_resolve_zone_config` to read `config["default_zone"]`,
  these tests failed with `KeyError: 'default_zone'`.
- **Fix:** Updated both helpers to use the `default_zone` sub-dict structure.
  Updated related assertions in `test_ws_set_zone_preheat_default` and
  `test_migration_room_preheat_to_zone`.
- **Files modified:** `tests/test_preheat.py`, `tests/test_calendar.py`
- **Commit:** b5f196f

## Verification

- `pytest tests/test_websocket.py`: 43 passed (run from worktree root)
- `pytest tests/`: 258 passed
- `grep -c 'global_time_program' websocket.py`: 0
- `grep -c '"global_mode"' websocket.py`: 0
- `websocket.py contains reset_room_to_default_zone_program`: 6 occurrences
- `ws_get_status calls _build_status_payload`: confirmed at line 180
- `make lint`: Passed

## Known Stubs

None — all data flows through the new default_zone schema with no hardcoded
empty values or placeholder text.

## Threat Flags

None — the WS command surface was reduced (2 commands removed), not expanded.
All remaining endpoints are protected by HA WebSocket auth gate (T-14-06,
accepted). The `set_zone_mode` sentinel for `zone_id="default"` preserves the
`vol.In(VALID_MODES)` schema gate (T-14-05, mitigated as planned).

## TDD Gate Compliance

- RED gate commit: 151760e (`test(14-03): add failing tests for default-zone
  WS command path`)
- GREEN gate commit: b5f196f (`feat(14-03): migrate WebSocket handlers to
  default-zone sub-dict path`)
- Both gates present in order.

## Self-Check: PASSED

- tests/test_websocket.py: exists, contains `reset_room_to_default_zone_program`,
  `set_zone_mode` with `"zone_id": "default"`, and removal tests for both
  `set_global_mode` and `reset_time_program`
- custom_components/climate_manager/websocket.py: `global_time_program` count=0,
  `"global_mode"` count=0, `reset_room_to_default_zone_program` present,
  `_build_status_payload()` call present at line 180
- custom_components/climate_manager/coordinator.py: `default_zone_preheat_enabled`
  flat key references removed from `_async_preheat_room`
- custom_components/climate_manager/storage.py: `preheat_from_gap01` guard
  present to handle GAP-01 + shim interaction
- Commits 151760e (RED) and b5f196f (GREEN) verified in git log

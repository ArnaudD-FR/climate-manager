---
plan: 05-01
phase: 05-zone-crud-evaluation-engine
status: complete
wave: 1
tasks_complete: 2/2
key-files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
requirements_covered:
  - ZONE-05
  - ZONE-06
  - ZONE-08
---

## Summary

Added three WebSocket handlers for zone CRUD: `create_zone`, `rename_zone`, `set_zone_mode`.
All follow the existing factory-closure + write-then-evaluate pattern. 14 total commands registered
(11 existing + 3 new). All 14 websocket tests green.

## Tasks

| Task | Status | Notes |
|------|--------|-------|
| Task 1 (RED tests) | ✓ | 5 failing tests committed (cherry-picked from partial prior run) |
| Task 2 (implementation) | ✓ | Handlers implemented inline; all 5 tests turned green |

## What Was Built

- `_make_ws_create_zone`: generates UUID, deepcopies `global_time_program` (D-02), stores under
  `runtime_config["zones"][zone_id]` with mode=`time_program` (D-01), returns full config (D-03)
- `_make_ws_rename_zone`: sentinel `zone_id="default"` routes to `runtime_config["default_zone_name"]`
  (D-05); unknown custom zone_id returns ERR_NOT_FOUND; never writes a "default" key into `zones{}`
- `_make_ws_set_zone_mode`: `vol.In(VALID_MODES)` schema gate rejects invalid modes before handler
  runs (T-05-02); ERR_NOT_FOUND for unknown or "default" zone_id

## Self-Check: PASSED

- `uv run pytest tests/test_websocket.py -x` → 14 passed
- `import uuid` added to stdlib imports block
- `copy.deepcopy(runtime_config["global_time_program"])` used (not DEFAULT_CONFIG)
- `runtime_config["default_zone_name"]` updated by rename_zone for Default Zone
- `websocket_api.ERR_NOT_FOUND` used for missing zone lookups
- 14 `async_register_command` calls in `async_register_commands`

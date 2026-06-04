---
phase: 15-remove-room-custom-scheduling
plan: "02"
subsystem: websocket
tags: [refactor, room-mode-removal, websocket, tdd]
dependency_graph:
  requires:
    - "15-01: ROOM_MODE_* constants deleted; coordinator/storage stripped"
  provides:
    - "websocket.py: reset_room_to_default_zone_program command removed (D-06)"
    - "websocket.py: ws_set_room_config silently drops room_mode (D-07)"
    - "tests/test_websocket.py: removed-command test for D-06; zero room_mode references"
  affects:
    - "websocket.py async_register_commands"
    - "websocket.py ws_set_room_config"
    - "tests/test_websocket.py Test 9 block"
tech_stack:
  added: []
  patterns:
    - "Silent pop() drop in ws_set_room_config (mirrors GAP-01 preheat_enabled pattern)"
    - "Removed-command WS test pattern (mirrors Phase 14 is_removed test)"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
decisions:
  - "Silent drop via incoming_config.pop('room_mode', None) — no schema rejection (D-07)"
  - "Removed-command test rewritten, not deleted — preserves coverage of absent command"
  - "test_set_room_config_null_zone_id_preserves_other_keys updated to drop room_mode from payload"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 15 Plan 02: WebSocket command removal + room_mode silent drop Summary

Removed the `reset_room_to_default_zone_program` WS command (factory +
registration + docstring), added silent `room_mode` drop in `ws_set_room_config`,
and cleaned all `room_mode` references from the websocket test suite. 249 tests
green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove reset command + add room_mode silent drop in websocket.py | 144f8fd | websocket.py |
| 2 | Update websocket tests for removed command + clean fixtures | 235f4c1 | test_websocket.py |

## Verified Must-Haves

- **D-06:** `reset_room_to_default_zone_program` command deleted — factory,
  registration, and docstring bullet removed; unregistered command returns
  `success: False`
- **D-07:** `ws_set_room_config` calls `incoming_config.pop("room_mode", None)`
  immediately after the `preheat_enabled` drop; no schema rejection (silent only)
- **D-14:** `test_ws_reset_room_to_default_zone_program_copies_into_room` deleted;
  Phase 15 `is_removed` test passes
- **D-15:** `room_mode` fixture keys removed from all surviving test fixtures;
  `grep -c 'room_mode' tests/test_websocket.py` → 0

## Deviations from Plan

None — plan executed exactly as written. The two fixture-cleanup tests
(`test_set_room_config_null_zone_id_is_idempotent_when_already_absent` and
`test_set_room_config_null_zone_id_preserves_other_keys`) were updated per
D-15 as specified: `room_mode` removed from both fixture seed dict and assertion.

## TDD Gate Compliance

The plan marks Task 2 as `tdd="true"`. The RED state was confirmed by running
`make test` after Task 1 committed: `test_ws_reset_room_to_default_zone_program
_copies_into_room` FAILED (1 failed, 220 passed) because the command was
unregistered. Task 2 implemented the GREEN state: test file rewritten so all
249 tests pass.

- RED state: confirmed by test run between Task 1 and Task 2 commits
- GREEN gate: 235f4c1 — all 249 tests pass

## Verification Results

```
grep -c '_make_ws_reset_room_to_default_zone_program' websocket.py  → 0
grep -c 'incoming_config.pop("room_mode", None)' websocket.py  → 1
grep -c 'room_mode' tests/test_websocket.py  → 0
make test  → 249 passed
make lint  → all Passed
```

## Self-Check: PASSED

- [x] websocket.py: 0 occurrences of `_make_ws_reset_room_to_default_zone_program`
- [x] websocket.py: contains `incoming_config.pop("room_mode", None)`
- [x] test_websocket.py: contains `def test_ws_reset_room_to_default_zone_program_is_removed`
- [x] test_websocket.py: does NOT contain `_copies_into_room`
- [x] test_websocket.py: 0 occurrences of `room_mode`
- [x] Commits 144f8fd, 235f4c1 exist in git log
- [x] 249 tests pass
- [x] All linting passes

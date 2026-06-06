---
phase: 260525-l0p
plan: "01"
subsystem: websocket-api, frontend-panel
tags: [defaults, reset, ws-commands, frontend-cleanup]
dependency_graph:
  requires: []
  provides:
    - climate_manager/reset_period_temperatures WS command
    - climate_manager/reset_time_program WS command
    - WsClient.resetPeriodTemperatures()
    - WsClient.resetTimeProgram()
  affects:
    - global-settings-tab.ts reset buttons
    - const.py (sole source of truth for defaults)
tech_stack:
  added: []
  patterns:
    - write-then-evaluate pattern for two new WS reset commands
    - shallow copy for dict defaults, deep copy for nested list defaults
key_files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
    - frontend/src/ws-client.ts
    - frontend/src/components/global-settings-tab.ts
    - custom_components/climate_manager/www/panel.js
decisions:
  - "Reset handlers use same-package import of _DEFAULT_DAILY_PROGRAM (option a)
    — no new public symbol in const.py"
  - "tempField helper defaultVal param removed; empty string shown while backend
    value loads (acceptable transient)"
  - "_onResetConfiguration calls resetTimeProgram() then
    setGlobalMode(MODE_TIME_PROGRAM) to mirror DEFAULT_GLOBAL_MODE"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-25T13:13:43Z"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 5
status: complete
---

# Quick Task 260525-l0p: Remove Hardcoded Frontend Defaults Summary

**One-liner:** Backend reset WS commands (reset*period_temperatures,
reset_time_program) with const.py as sole source of truth; all DEFAULT*\*
frontend constants deleted.

## Tasks Completed

| Task | Name                                                                     | Commit  | Status                      |
| ---- | ------------------------------------------------------------------------ | ------- | --------------------------- |
| 1    | Add reset_period_temperatures and reset_time_program WS handlers + tests | 3b0d2ae | Done                        |
| 2    | Add WsClient methods and strip frontend hardcoded defaults               | df5e64d | Done                        |
| 3    | Verify reset flow end-to-end in running HA                               | —       | Awaiting human verification |

## What Was Built

### Task 1 — Backend WS handlers + tests

**`custom_components/climate_manager/websocket.py`:**

- Added `import copy` and extended `.const` imports:
  `DEFAULT_PERIOD_TEMPERATURES`, `_DEFAULT_DAILY_PROGRAM`
- Added `_make_ws_reset_period_temperatures(entry)`: resets
  `runtime_config["period_temperatures"]` to `dict(DEFAULT_PERIOD_TEMPERATURES)`
  (shallow copy), then save / send_result / async_evaluate
- Added `_make_ws_reset_time_program(entry)`: resets
  `runtime_config["global_time_program"]` to
  `copy.deepcopy(_DEFAULT_DAILY_PROGRAM)`, then save / send_result /
  async_evaluate
- Both registered in `async_register_commands`; module docstring updated: 8 → 10
  commands

**`tests/test_websocket.py`:**

- Added `test_ws_reset_period_temperatures_writes_defaults`: mutates to 99.0
  values, sends reset, asserts equality with `DEFAULT_PERIOD_TEMPERATURES`,
  asserts no reference sharing
- Added `test_ws_reset_time_program_writes_defaults`: mutates to 1-day stub,
  sends reset, asserts all 7 day keys present with canonical starts ("00:00",
  "06:00", "22:00"), asserts deep equality with `_DEFAULT_DAILY_PROGRAM`,
  asserts deep copy isolation
- All 8 websocket tests pass

### Task 2 — WsClient methods + frontend cleanup

**`frontend/src/ws-client.ts`:**

- Added `resetPeriodTemperatures()`: sendMessagePromise with
  `type: "climate_manager/reset_period_temperatures"`, no payload
- Added `resetTimeProgram()`: sendMessagePromise with
  `type: "climate_manager/reset_time_program"`, no payload

**`frontend/src/components/global-settings-tab.ts`:**

- Deleted `DEFAULT_TEMPERATURES` constant (was {frost_protection: 5, reduced:
  18, normal: 20, comfort: 22})
- Deleted `DEFAULT_GLOBAL_MODE` constant (was "time_program")
- Deleted `DEFAULT_TIME_PROGRAM` constant + IIFE (7-day program)
- Rewrote `_onResetTemperatures`: now calls `ws.resetPeriodTemperatures()` then
  `reloadConfig()`
- Rewrote `_onResetConfiguration`: now calls `ws.resetTimeProgram()` +
  `ws.setGlobalMode(MODE_TIME_PROGRAM)` then `reloadConfig()`
- Removed `defaultVal: number` param from `tempField` helper; `.value` binding
  now `temps[id] != null ? String(temps[id]) : ""`
- Grep confirms 0 non-comment references to deleted constants remain

**Build:** `npm run build` succeeds, panel.js rebuilt (110.73 kB).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The `tempField` shows an empty string when backend value is absent, but
this is an intentional transient state (resolved once `reloadConfig()` completes
after any reset).

## Threat Flags

No new security surface introduced. Both reset commands use no payload (no
injection vector); all mutations are bounded to known const.py defaults.

## Self-Check

### Files exist:

- custom_components/climate_manager/websocket.py: present (modified)
- tests/test_websocket.py: present (modified)
- frontend/src/ws-client.ts: present (modified)
- frontend/src/components/global-settings-tab.ts: present (modified)
- custom_components/climate_manager/www/panel.js: present (rebuilt)

### Commits exist:

- 3b0d2ae: feat(260525-l0p-01): add reset_period_temperatures and
  reset_time_program WS handlers
- df5e64d: feat(260525-l0p-01): add WsClient reset methods and strip frontend
  hardcoded defaults

### Tests: 8/8 passed (uv run pytest tests/test_websocket.py -x -q)

## Self-Check: PASSED

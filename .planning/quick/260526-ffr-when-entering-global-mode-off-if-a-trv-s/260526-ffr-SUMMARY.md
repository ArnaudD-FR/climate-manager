---
phase: quick-260526-ffr
plan: "01"
subsystem: coordinator, trv
tags: [mode-off, hvac, trv-control, tdd]
dependency_graph:
  requires: []
  provides: [supports_hvac_off, set_trv_off, MODE_OFF per-TRV dispatch]
  affects: [coordinator.async_evaluate, trv.py]
tech_stack:
  added: [HVACMode import from homeassistant.components.climate]
  patterns: [anti-flap sentinel in _last_pushed, TDD RED/GREEN cycle]
key_files:
  created: []
  modified:
    - custom_components/climate_manager/trv.py
    - custom_components/climate_manager/coordinator.py
    - tests/test_trv.py
    - tests/test_coordinator.py
decisions:
  - Use "off" string sentinel in _last_pushed (dict widened to float|str) to prevent flapping without a separate data structure
  - supports_hvac_off checks HVACMode.OFF.value in hvac_modes attribute; missing/None attribute treated as False (fallback path, never raises)
  - set_trv_off issues only one service call (no set_temperature); mirrors set_trv_temperature availability guard
  - Leaving MODE_OFF requires no special code: the "off" != float comparison in _push_if_changed causes the push to fire on next tick
metrics:
  duration: "~20 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  files_changed: 4
---

# Quick Task 260526-ffr: MODE_OFF native TRV off support

**One-liner:** TRVs advertising HVACMode.OFF in hvac_modes now receive set_hvac_mode=off in MODE_OFF; TRVs without off support fall back to frost-protection setpoint as before.

## What Was Built

**trv.py additions:**

- `supports_hvac_off(hass, entity_id) -> bool`: reads `hvac_modes` attribute; returns `True` iff `"off"` is in the list. Returns `False` for missing state, missing attribute, or attribute not containing `"off"`. Never raises.
- `set_trv_off(hass, entity_id) -> None`: issues a single `climate.set_hvac_mode` call with `hvac_mode="off"`, `blocking=True`. Guards on unavailable/missing state (ROOM-03 parity). No `set_temperature` call.
- Added `HVACMode` import from `homeassistant.components.climate`.

**coordinator.py changes:**

- Import extended: `set_trv_off, supports_hvac_off` added alongside existing imports.
- `_last_pushed` annotation widened from `dict[str, float]` to `dict[str, float | str]`.
- MODE_OFF branch now dispatches per-entity: `_push_off_safely` for off-capable TRVs, `_push_safely` (frost-protection fallback) for others.
- New method `_push_off_safely(entity_id)`: availability guard + anti-flap check (`_last_pushed.get(entity_id) == "off"`) + `set_trv_off` call + sentinel write. Exception logged and swallowed.

## Test Coverage

All 31 tests pass (8 in test_trv.py, 23 in test_coordinator.py).

New tests added:

| File | Test | Verifies |
|------|------|----------|
| test_trv.py | test_supports_hvac_off_true_when_off_in_hvac_modes | supports_hvac_off returns True |
| test_trv.py | test_supports_hvac_off_false_when_attribute_missing | supports_hvac_off returns False |
| test_trv.py | test_set_trv_off_issues_single_set_hvac_mode_off_call | single hvac call, zero temp calls |
| test_trv.py | test_set_trv_off_skips_unavailable_entity | ROOM-03 guard |
| test_coordinator.py | test_mode_off_uses_set_hvac_mode_off_when_supported | off-capable TRV gets set_hvac_mode=off |
| test_coordinator.py | test_mode_off_falls_back_to_frost_temp_when_off_not_supported | heat-only TRV gets frost temp |
| test_coordinator.py | test_mode_off_does_not_flap_set_hvac_mode_off_on_repeat_tick | anti-flap sentinel works |

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 5a609e1 | test(260526-ffr-01): add failing tests for supports_hvac_off and set_trv_off |
| efc6234 | feat(260526-ffr-01): add supports_hvac_off and set_trv_off helpers to trv.py |
| b535a84 | test(260526-ffr-01): add failing tests for coordinator MODE_OFF per-TRV dispatch |
| aef5cee | feat(260526-ffr-01): dispatch per-TRV in coordinator MODE_OFF branch |

## Self-Check

- [x] custom_components/climate_manager/trv.py — modified (supports_hvac_off, set_trv_off added)
- [x] custom_components/climate_manager/coordinator.py — modified (_push_off_safely, MODE_OFF dispatch)
- [x] tests/test_trv.py — 4 new tests, all passing
- [x] tests/test_coordinator.py — 3 new tests, all passing
- [x] All 4 commits verified in git log

## Self-Check: PASSED

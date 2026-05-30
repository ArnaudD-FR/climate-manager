---
plan: 09-02
phase: 09
status: complete
completed: 2026-05-30
---

# Plan 09-02 Summary — Coordinator Calibration Engine

## What Was Built

Added the TRV offset calibration engine to `coordinator.py` and the two
DEFAULT_CONFIG keys to `const.py`.

### Files Modified

- `custom_components/climate_manager/const.py` — two new top-level keys in
  `DEFAULT_CONFIG`: `calibration_enabled: False`, `calibration_threshold: 0.5`
- `custom_components/climate_manager/coordinator.py` — new imports
  (`set_trv_offset`, `supports_offset_calibration`) + `_async_calibrate()` +
  `_async_calibrate_room()` private methods; `async_evaluate()` calls
  `_async_calibrate(config)` at the end (after push pass and status fire)
- `tests/test_coordinator.py` — 8 new calibration tests, all passing

### Key Implementation Details

- **D-01/D-02:** `await self._async_calibrate(config)` added as the final line
  of `async_evaluate()`, inheriting the existing 1-minute cadence — no
  separate timer needed
- **D-04:** Early return in `_async_calibrate` when `calibration_enabled` is
  False — zero attribute reads, zero service calls
- **D-03:** `asyncio.gather()` over all rooms exactly mirroring the push pass
  concurrency pattern
- **D-08:** `supports_offset_calibration` check: attribute-first
  (`temperature_offset` in `state.attributes`), then
  `hass.services.has_service("tado_x", "set_temperature_offset")` — correct
  order per Pitfall 3
- **D-05/D-06/D-07:** `delta = sensor_temp - current_temp`; only applied when
  `abs(delta) > threshold`; `new_offset = existing_offset + delta`
- **Pitfall 2:** `current_temperature is None` guard before float cast
- **Pitfall 5:** Sensor state `"unavailable"/"unknown"` guard + `try/except
  (ValueError, TypeError)` around `float()` cast

### TDD Gates

- **RED commit:** `520a8dd` — 8 tests added, 1 failing (delta above threshold)
- **GREEN commit:** `e1ca3ca` — all 8 tests pass

## Self-Check: PASSED

- All 8 calibration tests pass
- Full suite: 146 tests, 1 pre-existing failure in test_phase06_acceptance.py
  (unrelated to Phase 9 — tab label whitespace mismatch predates this phase)
- No STATE.md / ROADMAP.md modifications (orchestrator owns those)

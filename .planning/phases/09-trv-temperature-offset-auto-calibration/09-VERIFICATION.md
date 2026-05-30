---
phase: 09-trv-temperature-offset-auto-calibration
verified: 2026-05-30T14:00:00Z
status: human_needed
score: 4/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Confirm Options card (ha-switch) is visible in HA 2026.x and calibration toggle persists across page reload"
    expected: "A third 'Options' card appears in the Global Settings tab with a visible toggle. Enabling it shows a 'Saved' toast; after reload the toggle stays ON. Disabling and reloading shows it stays OFF."
    why_human: "ha-switch is known to render invisibly in HA 2026.x (same breakage as ha-textfield, ha-select, ha-tabs). Cannot verify DOM rendering programmatically. This is Pitfall 6 from the PLAN."
---

# Phase 09: TRV Temperature Offset Auto-Calibration — Verification Report

**Phase Goal:** When enabled, the integration periodically corrects each compatible TRV's
temperature offset so its readings track the room's reference sensor, while silently leaving
incompatible or sensor-less rooms untouched and avoiding jittery over-correction.

**Verified:** 2026-05-30T14:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can enable/disable TRV offset auto-calibration globally from the Global Settings tab, and the setting persists across restarts | ? UNCERTAIN | Implementation confirmed (websocket.py:1011-1017 mutates runtime_config + calls store.async_save; WS tests verify mutation; ha-switch UI needs human confirmation — see Human Verification) |
| 2 | When calibration is enabled and a room has both a reference sensor and a compatible TRV, the coordinator periodically applies an offset so the TRV's reported temperature converges toward the reference sensor | ✓ VERIFIED | `_async_calibrate` called from `async_evaluate` line 284 after push pass; `_async_calibrate_room` implements full delta/threshold/incremental-offset logic; test `test_calibration_delta_above_threshold_one_offset_call` confirms `new_offset = existing(0.5) + delta(1.0) = 1.5` |
| 3 | Rooms whose TRV does not support offset adjustment (no `temperature_offset` attribute AND no `tado_x.set_temperature_offset` service) are skipped with no error or log spam | ✓ VERIFIED (with WARNING) | `supports_offset_calibration` guard in `_async_calibrate_room` (line 320) returns False when both conditions absent; test `test_calibration_incompatible_trv_zero_offset_calls` passes. WARNING: CR-01 — a non-Tado TRV that has `temperature_offset` attribute but lacks the `tado_x` service passes the guard but produces a `_LOGGER.warning` every minute (ServiceNotFound caught by BLE001). Primary Tado X hardware is unaffected. |
| 4 | Rooms without a reference temperature sensor configured are skipped — no offset is ever applied to them | ✓ VERIFIED | `_async_calibrate_room` line 314: `if not sensor_entity_id: return`; test `test_calibration_no_sensor_zero_offset_calls` confirms zero offset calls |
| 5 | An offset is applied only when the measured delta exceeds the configurable threshold (default 0.5°C), so small fluctuations do not cause repeated offset changes | ✓ VERIFIED | `threshold = config.get("calibration_threshold", 0.5)` at coordinator.py line 353; `if abs(delta) <= threshold: return` at line 354-355; `calibration_threshold: 0.5` in DEFAULT_CONFIG (const.py line 195); tests `test_calibration_delta_below_threshold_zero_offset_calls` and `test_calibration_delta_above_threshold_one_offset_call` both pass |

**Score:** 4/5 truths fully verified (truth 1 has a human-gated UI component)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/climate_manager/trv.py` | `supports_offset_calibration` and `set_trv_offset` functions | ✓ VERIFIED | Both functions present at lines 119-167. Attribute-first guard order implemented. |
| `custom_components/climate_manager/coordinator.py` | `_async_calibrate` and `_async_calibrate_room` methods, wired into `async_evaluate` | ✓ VERIFIED | Both methods present at lines 286-371; `await self._async_calibrate(config)` called at line 284, after `async_fire` (line 278). |
| `custom_components/climate_manager/const.py` | `calibration_enabled` and `calibration_threshold` in `DEFAULT_CONFIG` | ✓ VERIFIED | Lines 194-195: `"calibration_enabled": False` and `"calibration_threshold": 0.5` |
| `custom_components/climate_manager/websocket.py` | `_make_ws_set_calibration_config` factory registered | ✓ VERIFIED | Factory at line 987; registration at line 117; schema uses `vol.Required("enabled"): bool` |
| `tests/test_trv.py` | 7 unit tests for both TRV functions | ✓ VERIFIED | Tests 9-15 at lines 155-227; all pass |
| `tests/test_coordinator.py` | 8 calibration unit tests | ✓ VERIFIED | Tests at lines 1439-1756; all 8 pass |
| `tests/test_websocket.py` | 2 WS command tests | ✓ VERIFIED | Tests at lines 1126-1168; both pass |
| `frontend/src/types.ts` | `calibration_enabled` and `calibration_threshold` on `ClimateConfig` | ✓ VERIFIED | Lines 74-77: both optional fields present with JSDoc |
| `frontend/src/ws-client.ts` | `setCalibrationConfig(enabled)` method | ✓ VERIFIED | Lines 201-207: method present, calls `climate_manager/set_calibration_config` |
| `frontend/src/components/global-settings-tab.ts` | `_renderOptionsCard` with calibration toggle | ✓ VERIFIED | Lines 525-543: Options card present as third card in `render()` (line 548) |
| `custom_components/climate_manager/www/panel.js` | Built artifact with calibration code | ✓ VERIFIED | Contains `setCalibrationConfig`, `calibration_enabled`, `ha-switch`, `_onCalibrationToggle` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `async_evaluate` | `_async_calibrate` | `await self._async_calibrate(config)` at line 284 | ✓ WIRED | Called after push pass and `async_fire` — correct position |
| `_async_calibrate_room` | `set_trv_offset` | incremental offset then `await set_trv_offset(...)` at line 367 | ✓ WIRED | Guarded by threshold, wrapped in `try/except Exception` |
| `_async_calibrate` | `calibration_enabled` | `config.get("calibration_enabled", False)` at line 292 | ✓ WIRED | Early return when disabled |
| `_make_ws_set_calibration_config` | `runtime_config["calibration_enabled"]` | single-key mutation then `store.async_save` | ✓ WIRED | Lines 1011-1016 |
| `async_register_commands` | `_make_ws_set_calibration_config` | `websocket_api.async_register_command(hass, _make_ws_set_calibration_config(entry))` | ✓ WIRED | Line 117 |
| `global-settings-tab _onCalibrationToggle` | `ws.setCalibrationConfig` | arrow function, change event → WS call → reloadConfig → toast | ✓ WIRED | Lines 362-371 |
| `setCalibrationConfig` | `climate_manager/set_calibration_config` | `sendMessagePromise` | ✓ WIRED | ws-client.ts lines 202-207 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `global-settings-tab.ts` `_renderOptionsCard` | `this.config.calibration_enabled` | `ClimateConfig` from `getConfig()` WS call, populated from `runtime_config["calibration_enabled"]` | Yes — runtime_config is written by `store.async_save` | ✓ FLOWING |
| `coordinator.py` `_async_calibrate_room` | `sensor_temp`, `current_temp`, `existing_offset` | Live HA state via `hass.states.get()` | Yes — reads live entity attributes | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All phase-relevant Python tests pass | `pytest tests/test_trv.py tests/test_coordinator.py tests/test_websocket.py -q` | 81 passed, 0 failed | ✓ PASS |
| Panel.js contains calibration UI code | `grep -c "setCalibrationConfig\|calibration_enabled\|_renderOptionsCard\|set_calibration_config" panel.js` | 6 matches | ✓ PASS |
| ha-switch renders and toggle works in HA 2026.x | Manual HA 2026.x inspection | Not testable programmatically | ? SKIP (see Human Verification) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CALIB-01 | 09-03, 09-04 | User can enable/disable TRV offset auto-calibration globally | ✓ SATISFIED | `set_calibration_config` WS command registered; UI toggle in `_renderOptionsCard`; setting lands in `runtime_config` and is saved via `store.async_save` |
| CALIB-02 | 09-01, 09-02 | Coordinator periodically computes delta and calls offset service if TRV supports it | ✓ SATISFIED | `_async_calibrate_room` computes `delta = sensor_temp - current_temp`, checks threshold, calls `set_trv_offset` with `new_offset = existing_offset + delta` |
| CALIB-03 | 09-01, 09-02 | Capability guard detects TRV offset support; incompatible rooms silently skipped | ✓ SATISFIED (with WARNING) | `supports_offset_calibration` implemented with attribute-first guard; all 4 test cases pass. CR-01 causes log warnings for non-Tado TRVs with `temperature_offset` attribute — primary hardware unaffected. |
| CALIB-04 | 09-02 | Minimum delta threshold (default 0.5°C) prevents jitter | ✓ SATISFIED | `calibration_threshold: 0.5` in DEFAULT_CONFIG; threshold used in coordinator; two tests verify boundary condition |
| CALIB-05 | 09-02 | Calibration only runs when room has a configured reference sensor | ✓ SATISFIED | `if not sensor_entity_id: return` guard first in `_async_calibrate_room`; test confirms zero calls without sensor |

All 5 CALIB requirements satisfied. REQUIREMENTS.md traceability column lists all CALIB-* as "Phase 9, TBD" — plan numbers not yet back-filled in the table. This is a documentation gap in REQUIREMENTS.md, not a code gap.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `custom_components/climate_manager/trv.py` | 162-166 | `set_trv_offset` always calls `tado_x.set_temperature_offset` unconditionally — no routing branch for non-Tado TRVs detected via attribute path | ⚠️ Warning (CR-01) | Non-Tado TRVs with `temperature_offset` attribute but no `tado_x` service will receive a `_LOGGER.warning` every calibration tick. Primary Tado X hardware is unaffected. |
| `custom_components/climate_manager/websocket.py` | 1011-1017 | `set_calibration_config` mutates `runtime_config` before `store.async_save` with no try/except rollback (unlike all other write handlers) | ⚠️ Warning (CR-02) | If `async_save` raises (I/O error), in-memory state diverges from stored state until next restart. Normal flow is unaffected. |
| `frontend/src/types.ts` | 77 | `calibration_threshold?: number` declared but no WS mutation command exists for it | ℹ️ Info (WR-04) | Dead type field creates misleading contract; the value is stuck at default 0.5 with no UI path to change it. |

No `TBD`, `FIXME`, or `XXX` markers found in any modified file.

---

### Human Verification Required

#### 1. Options Card and Toggle Visibility in HA 2026.x (Pitfall 6)

**Test:** Open the live HA 2026.x instance (homeassistant.local), navigate to the
Climate Manager panel, then go to the Global Settings tab.

**Expected:**
1. A third card titled "Options" appears below the "Temperatures" card.
2. A toggle labeled "Auto-calibrate TRV temperature offsets" is VISIBLE inside the card.
   (If `ha-switch` renders nothing — same breakage as `ha-textfield`/`ha-tabs`/`ha-select` in HA 2026.x — apply the native `<input type="checkbox">` fallback before approving.)
3. Toggling the switch ON shows a "Saved" toast.
4. Reloading the page: the switch remains ON (persisted across reload).
5. Toggling OFF and reloading: the switch remains OFF.

**Why human:** `ha-switch` is not confirmed safe in HA 2026.x (WR-03 from code review).
The project memory records that `ha-textfield`, `ha-tabs`, and `ha-select` silently break in
HA 2026.x. `ha-switch` has not been affirmatively verified. DOM rendering and event behavior
cannot be verified programmatically without a live browser session.

---

### Gaps Summary

No blocking gaps identified. The phase goal is implemented and all 5 CALIB requirements
have evidence in the codebase. Two code review findings (CR-01, CR-02) are real bugs but
are classified as warnings:

- **CR-01** (set_trv_offset routing): Affects non-Tado TRVs with `temperature_offset`
  attribute but no `tado_x` service — produces log warnings per tick instead of silent skip.
  The primary Tado X hardware path is correct. This is an edge-case defect for non-primary
  hardware, not a blocker for the phase goal.

- **CR-02** (no rollback on save failure): Affects the `set_calibration_config` WS handler
  only when `store.async_save` raises (I/O error). Normal operation is unaffected. The
  inconsistency is self-correcting on restart.

Both bugs are actionable improvements but do not prevent the core calibration goal from
functioning on the target hardware.

The status is `human_needed` solely because `ha-switch` visibility in HA 2026.x has not
been confirmed (Pitfall 6 / WR-03). All automated checks pass.

---

_Verified: 2026-05-30T14:00:00Z_
_Verifier: Claude (gsd-verifier)_

---
phase: 09-trv-temperature-offset-auto-calibration
fixed_at: 2026-05-30T00:00:00Z
review_path: .planning/phases/09-trv-temperature-offset-auto-calibration/09-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 5
skipped: 1
status: partial
---

# Phase 09: Code Review Fix Report

**Fixed at:** 2026-05-30
**Source review:** .planning/phases/09-trv-temperature-offset-auto-calibration/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 Critical, 4 Warning)
- Fixed: 5
- Skipped: 1

## Fixed Issues

### CR-01: `set_trv_offset` always calls `tado_x` service even for non-Tado TRVs

**Files modified:** `custom_components/climate_manager/trv.py`
**Commit:** 94574ac
**Applied fix:** `supports_offset_calibration` now requires BOTH the
`temperature_offset` attribute AND the `tado_x` service to be present. A
TRV with the attribute but no service has no write path, so `False` is
returned — preventing the calibration loop from scheduling calls against a
non-existent service. `set_trv_offset` adds an explicit `has_service` guard
before the `async_call`, returning silently when the service is absent. This
stops the silent `ServiceNotFound` log flood for non-Tado brand TRVs.

### CR-02: `set_calibration_config` mutates in-memory state before `async_save` with no rollback

**Files modified:** `custom_components/climate_manager/websocket.py`
**Commit:** 8273314
**Applied fix:** Added the snapshot/restore pattern matching all other write
handlers: capture `old_value` before mutation, wrap `async_save` in
`try/except Exception`, restore the old value and call `send_error` on
failure, return before `send_result`. On success, `send_result` fires as
before. Ruff auto-formatted the indentation on first commit attempt; the
re-staged version passed all hooks.

### WR-01: New TRV functions miss the `"unknown"` state guard

**Files modified:** `custom_components/climate_manager/trv.py`
**Commit:** 94574ac (committed together with CR-01 — same file)
**Applied fix:** Extended all three availability guards in `set_trv_temperature`,
`set_trv_off`, and `set_trv_offset` from `state.state == "unavailable"` to
`state.state in ("unavailable", "unknown")`, matching the established
coordinator sensor guard pattern.

### WR-02: Calibration offset accumulates without an upper/lower clamp

**Files modified:** `custom_components/climate_manager/coordinator.py`
**Commit:** b643e74
**Applied fix:** Added module-level constant `_OFFSET_CLAMP = 5.0` after
`POLL_INTERVAL`, and replaced the bare `new_offset = existing_offset + delta`
assignment with `new_offset = max(-_OFFSET_CLAMP, min(_OFFSET_CLAMP,
existing_offset + delta))`. This caps the offset at ±5°C before each
`set_trv_offset` call, preventing runaway accumulation and keeping values
within the hardware-accepted range for Tado X and common TRV brands.

### WR-04: `calibration_threshold` typed in `ClimateConfig` but no mutation path exists

**Files modified:** `frontend/src/types.ts`
**Commit:** ae8786a
**Applied fix:** Expanded the inline JSDoc comment on
`ClimateConfig.calibration_threshold` to add a `TODO(phase-10)` note
explaining that no mutation path (WS command or UI control) exists in this
phase. The field is retained because the backend seeds it in `DEFAULT_CONFIG`
and it surfaces in `get_config` responses. The comment prevents the
misleading implication that the field is currently user-configurable.

## Skipped Issues

### WR-03: `ha-switch` component API not verified for HA 2026.x

**File:** `frontend/src/components/global-settings-tab.ts:535-538`
**Reason:** acknowledged — already resolved by human verification. The
project owner confirmed `ha-switch` works correctly in HA 2026.x (the
`change` event correctly exposes `event.target.checked`). No code change is
needed; no defensive fallback is required given the verified behavior. Marked
as acknowledged per the review instructions.
**Original issue:** `ha-switch` `checked` property behavior unverified in
HA 2026.x; risk of `undefined` being passed to `setCalibrationConfig`.

---

_Fixed: 2026-05-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

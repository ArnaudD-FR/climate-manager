---
status: resolved
trigger: fire set_hvac_mode=heat and set_temperature only when not already set
created: "2026-05-31"
updated: "2026-05-31"
---

# Debug Session: skip-redundant-hvac-and-temp-calls

## Symptoms

- **Expected:** `set_trv_temperature` only calls `set_hvac_mode=heat` when the TRV is not already in heat mode, and only calls `set_temperature` when the setpoint differs from the desired value. This halves the tado_x API writes on steady-state (all TRVs already heating).
- **Actual:** `set_trv_temperature` in `custom_components/climate_manager/trv.py` unconditionally fires both service calls every time — even when `state.state == "heat"` and/or the setpoint is already correct.
- **Impact:** Each push cycle generates 2 tado_x API writes per room (22 total for 11 rooms), each triggering a `tado_x.async_request_refresh()`. On steady-state (no period transition, TRVs already at correct temp), the coordinator's D-02/D-03 guards prevent `set_trv_temperature` from being called at all. But on startup or period transitions, 11 rooms × 2 calls = 22 writes when only 11 (or 0) are needed.

## Evidence

- timestamp: "2026-05-31T14:16:52"
  observation: "11× POST /manualControl fired (set_hvac_mode=heat, step 1)"
  source: ha_logs

- timestamp: "2026-05-31T14:16:53"
  observation: "11× POST /manualControl fired (set_temperature, step 2) — even though TRVs likely already in heat mode"
  source: ha_logs

- timestamp: "2026-05-31T14:16:52"
  observation: "set_trv_temperature in trv.py:64 calls set_hvac_mode unconditionally (no state.state check)"
  source: code_inspection (trv.py lines 64-70)

- timestamp: "2026-05-31T15:51:00"
  observation: "Adding Guard B (skip set_temperature when reported setpoint == desired) regressed test_zone_mode_time_program_uses_zone_schedule: climate.d_trv was seeded at temperature=20.0 while the Default Zone Normal schedule resolves to 20.0, so the guard suppressed the call and the 'Expected set_temperature call for d_trv' assertion failed."
  source: pytest (make test)

## Eliminated

- The coordinator's D-02 `_push_if_changed` guard already prevents redundant
  `set_trv_temperature` calls on steady-state, but it does NOT cover startup /
  period transitions where every room is pushed. The self-contained guards in
  `set_trv_temperature` are still needed for those cases.

## Current Focus

hypothesis: "Both guards belong in set_trv_temperature: skip set_hvac_mode when already 'heat', and skip set_temperature when the reported 'temperature' attribute already equals the desired value (missing attribute => issue the call)."
test: "Unit + coordinator tests assert guards skip/fire correctly. test_zone_mode_time_program_uses_zone_schedule must keep d_trv's push firing while still proving the coordinator picks 20.0 for the Default Zone."
expecting: "RED before fix, GREEN after."
next_action: "Done."

## Resolution

root_cause: "set_trv_temperature unconditionally issued both climate.set_hvac_mode=heat and climate.set_temperature on every push, doubling tado_x API writes on startup and period transitions; there was no per-call redundancy guard inside the helper."
fix: "Guard A — skip set_hvac_mode when state.state is already 'heat' (still fires for any non-heat mode per the Tado X auto-mode workaround, INFRA-04). Guard B — skip set_temperature when the reported 'temperature' attribute already equals the desired value; missing attribute means the setpoint cannot be proven so the call is issued. Fixed the regressed coordinator test by seeding climate.d_trv at 18.0 instead of 20.0 so the push still fires (18.0 != desired 20.0) while the assertion still verifies the coordinator resolves 20.0 for the Default Zone."
verification: "make test — target tests test_zone_mode_time_program_uses_zone_schedule and test_global_mode_off_does_not_affect_custom_zones pass GREEN. Baseline (test edit reverted) showed this test RED; with the fix it is GREEN. 3 unrelated pre-existing failures (calibration offset rounding + panel overview label) belong to separate uncommitted changes in the working tree and are present in both baseline and fixed runs."
files_changed:
  - custom_components/climate_manager/trv.py
  - tests/test_coordinator.py
</content>
</invoke>

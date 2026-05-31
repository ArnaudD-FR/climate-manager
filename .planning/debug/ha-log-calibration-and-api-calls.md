---
status: resolved
trigger: fix issues detected in ha logs
created: "2026-05-31"
updated: "2026-05-31"
---

# Debug Session: ha-log-calibration-and-api-calls

## Symptoms

- **Expected:** Tado X calibration offset applied cleanly; tado_x coordinator performs 3 API calls per scheduled refresh cycle.
- **Actual:** Two distinct issues observed in live HA logs:

### Issue 1 — Calibration offset precision error (recurring every ~1 min before restart)
```
ERROR Failed to set temperature offset for device VA3805450240:
  API error: 400 - {"errors":[{"code":"bad.request","title":"temperature should have only one digit after the decimal point"}]}
ERROR Failed to set temperature offset for device VA1490259968:
  API error: 400 - {"errors":[{"code":"bad.request","title":"temperature should have only one digit after the decimal point"}]}
```
- Both Tado X Radiator Valve X devices affected
- Fires every minute (each calibration tick)

### Issue 2 — Extra API calls per climate_manager push (observed after restart)
```
#64 GET /rooms
#65 GET /roomsAndDevices
#66 GET /state
-- climate_manager push fires --
#67-77  POST /rooms/{1,2,4,5,7,8,9,10,11,12,13}/manualControl  (11 rooms)
#78     GET /rooms      ← reactive refresh triggered by state change
#79-88  POST /rooms/{...}/manualControl  (10 more rooms)
#89     GET /roomsAndDevices
#90     GET /state
#91     POST /rooms/11/manualControl
#92     GET /rooms      ← another reactive refresh 10s later
#93     GET /roomsAndDevices
#94     GET /state
```
- Expected: 3 base calls per interval. climate_manager push = 11 additional POSTs (one per room, push-on-change).
- Actual: 3 base + 11 push + ~14 reactive (state-change-triggered refetch + second push batch) = ~28 calls per push cycle

## Evidence

- timestamp: "2026-05-31T13:56:01"
  observation: "Calibration 400 error for VA3805450240 — bad decimal precision"
  source: ha_logs

- timestamp: "2026-05-31T14:16:52"
  observation: "11 POST manualControl calls burst from climate_manager push"
  source: ha_logs

- timestamp: "2026-05-31T14:16:53"
  observation: "Reactive GET rooms + 10 more POSTs triggered 1s after push"
  source: ha_logs

- timestamp: "2026-05-31T15:30:00"
  observation: "coordinator.py device path (_async_calibrate_tado_device, line 452) already rounds to 1 decimal via commit de97729 (already in HEAD). Entity path (_async_calibrate_room, line 531) does NOT round. Both trv.py helpers (set_trv_offset, set_trv_offset_by_device) passed offset through verbatim — the true root-cause boundary."
  source: code_inspection

- timestamp: "2026-05-31T15:35:00"
  observation: "tado_x climate.py calls coordinator.async_request_refresh() after every write (async_set_temperature/async_set_hvac_mode). 11-room climate_manager push burst = 11+ refresh requests, each a GET /rooms+/roomsAndDevices+/state. Standard HA refresh-after-write pattern; default debouncer (0.3s) does not coalesce a multi-second serial burst."
  source: code_inspection

- timestamp: "2026-05-31T15:45:00"
  observation: "TDD RED: test_set_trv_offset_rounds_to_one_decimal + test_set_trv_offset_by_device_rounds_to_one_decimal fail (sent 0.22, expected 0.2). GREEN after round(offset, 1) added to both helpers. 2 new tests pass; pre-existing socket-blocked failures unrelated (fail on clean HEAD too)."
  source: test_run

## Eliminated

- climate_manager does NOT subscribe to tado_x state-change events. The Issue 2 "second push batch" is not climate_manager reacting to tado_x — it is the tado_x coordinator's own refresh-after-write behaviour. Confirmed: climate_manager evaluates on a 1-minute timer + startup only, using push-on-change (_last_pushed dict).
- Issue 1 device-path-only rounding was already partially fixed (commit de97729). That alone was insufficient because the entity path and the helper boundary were still unrounded.

## Current Focus

hypothesis: "RESOLVED — Issue 1 root cause = offset float arithmetic produced >1 decimal value sent verbatim to the Tado X API; the only guaranteed fix is to round at the API boundary (trv.py helpers) so every caller is covered. Issue 2 = expected HA coordinator refresh-after-write behaviour on the tado_x side, not a climate_manager defect."
test: "TDD test asserting both trv.py offset helpers round to 1 decimal before calling tado_x.set_temperature_offset."
expecting: "RED before fix (0.22 sent), GREEN after round(offset, 1)."
next_action: "Done — fix applied and verified."

## Specialist Review

specialist_hint: python
Result: LOOKS_GOOD — rounding at the service-call boundary in trv.py is the
idiomatic, defense-in-depth fix: it protects both the device path and the
entity path (the latter still lacked rounding) and any future caller, rather
than relying on each call site to round. round(offset, 1) is safe — verified
that round(x, 1) never produces a JSON representation with more than one
decimal across the full clamped offset range (±5.0).

## Resolution

root_cause: "Issue 1 — calibration offset computed via float arithmetic (existing_offset + delta) can yield values with more than one decimal place (e.g. 0.22); these were passed verbatim to tado_x.set_temperature_offset, which the Tado X API rejects with 400 'temperature should have only one digit after the decimal point'. The device path was already rounded (commit de97729) but the entity path and both trv.py helper boundaries were not. Issue 2 — not a climate_manager defect: the tado_x coordinator issues async_request_refresh() after each write (standard HA refresh-after-write), so a multi-room climate_manager push burst produces one refresh per write; the default 0.3s debouncer cannot coalesce a serial multi-second burst."
fix: "Round the offset to one decimal place at the API boundary in both trv.py helpers (set_trv_offset and set_trv_offset_by_device) via round(offset, 1), protecting every caller including the unrounded entity path. Issue 2 left as-is: it is correct/expected HA coordinator behaviour and any mitigation belongs in ha-tado-x (e.g. larger request_refresh debouncer cooldown), not climate_manager — flagged but not changed to avoid breaking refresh correctness."
verification: "TDD RED→GREEN: tests/test_trv.py::test_set_trv_offset_rounds_to_one_decimal and ::test_set_trv_offset_by_device_rounds_to_one_decimal fail before the fix (0.22 sent) and pass after. make lint passes (ruff, ruff-format, prettier, markdownlint). 2 pre-existing socket-blocked test failures confirmed unrelated (fail identically on clean HEAD)."
files_changed:
  - custom_components/climate_manager/trv.py
  - tests/test_trv.py

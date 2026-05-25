---
slug: boiler-temp-pushed-like-trv
status: resolved
trigger: "boiler temperature should not be updated like TRV. See this log: 2026-05-25 15:07:50.431 WARNING (MainThread) [custom_components.climate_manager.coordinator] Failed to push temperature to climate.e3_vitodens_200_0821_heating in MODE_TIME_PROGRAM"
created: 2026-05-25
updated: 2026-05-25
---

## Symptoms

- **Expected:** Only TRV entities (max_temp <= 45°C) receive temperature push calls from the coordinator
- **Actual:** Boiler entity `climate.e3_vitodens_200_0821_heating` (Viessmann vicare, max_temp=60°C) also receives push calls, causing WARNING logs and failed attempts
- **Error:** `Failed to push temperature to climate.e3_vitodens_200_0821_heating in MODE_TIME_PROGRAM`
- **Timeline:** Always present — `is_trv_entity()` was added to `trv.py` but only used for the `has_trv` status flag, never in the actual push loops
- **Reproduction:** Any schedule evaluation tick in MODE_TIME_PROGRAM or MODE_TIME_PROGRAM_PRESENCES

## Current Focus

hypothesis: "Both push loops in coordinator.py (_evaluate_time_program line 222, _evaluate_time_program_presences lines 357-362) iterate over all entity_ids without calling is_trv_entity(). The function exists in trv.py and is imported in coordinator.py for _build_status_payload, but is not applied before building the pushes list."
test: "Search for the push accumulation patterns in coordinator.py"
expecting: "Lines 222 and 357-362 do not filter by is_trv_entity()"
next_action: "RESOLVED — fix applied and tests pass"
root_cause_found: true

## Evidence

- timestamp: 2026-05-25T13:15:00
  observation: "coordinator.py line 222: `pushes.extend((entity_id, desired_temp) for entity_id in entity_ids)` — no is_trv_entity() guard"
  rules_out: "filter applied elsewhere"

- timestamp: 2026-05-25T13:15:10
  observation: "coordinator.py lines 357-362: same pattern, no is_trv_entity() guard"
  rules_out: "filter applied in presences path"

- timestamp: 2026-05-25T13:15:20
  observation: "is_trv_entity() is imported (line 56) and used only on line 415 (_build_status_payload has_trv flag)"
  rules_out: "function missing"

- timestamp: 2026-05-25T14:00:00
  observation: "is_trv_entity() in trv.py had an overly strict guard: returned False when current_temperature attribute was absent, causing valid TRV entities without sensor data to be excluded"
  rules_out: "fix is complete with trv.py guard removed"

## Eliminated

- hypothesis: "is_trv_entity() is called before pushing"
  eliminated_by: "code reading confirms no call in push loops"

## Resolution

root_cause: "Push loops in coordinator.py do not filter entities by is_trv_entity() before pushing temperatures. The is_trv_entity() utility exists and is imported but is only used for the has_trv status flag. Additionally, is_trv_entity() had a secondary bug: it returned False when current_temperature was absent, which would exclude valid TRVs that haven't reported sensor data yet."
fix: "1) Added `if is_trv_entity(self._hass, entity_id)` guard in both push loops: line 222 (_evaluate_time_program) and line 361 (_evaluate_time_program_presences). 2) Fixed is_trv_entity() in trv.py to use only max_temp <= 45 as the discriminator, removing the incorrect current_temperature guard. All 84 tests pass."
files_changed:
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/trv.py

## Summary

The boiler entity `climate.e3_vitodens_200_0821_heating` (Viessmann vicare, max_temp=60°C) was receiving temperature push calls because both schedule evaluation loops in `coordinator.py` iterated over all `entity_ids` without calling `is_trv_entity()`. The filter function existed and was imported but only used for the `has_trv` status flag.

A secondary bug was found during fix application: `is_trv_entity()` in `trv.py` returned `False` when the entity's `current_temperature` attribute was absent, which would silently exclude valid TRVs that haven't reported sensor data yet. This guard was removed; the `max_temp <= 45` threshold is the sole discriminator.

Fix applied to two files in one atomic commit. All 84 tests pass.

---
status: resolved
slug: present-persons-not-shown-in-status
trigger: "I defined a person as present but the 'present persons' in current status of global settings does not reflect it"
created: 2026-05-21
updated: 2026-05-21
---

# Debug Session: present-persons-not-shown-in-status

## Symptoms

- **Expected:** Setting a person's mode to "present" in the Persons tab should show that person under "Present persons" in the Global Settings Current Status card
- **Actual:** "Present persons" shows "No one home"
- **Errors:** None
- **Timeline:** Unknown — likely always the case
- **Reproduction:** Set global mode to "Time program", set a person to "present" mode in Persons tab → "Present persons" in status shows "No one home"

## Gathered Context

- Global mode: TIME_PROGRAM (not TIME_PROGRAM_PRESENCES)
- Set via: Persons tab in Climate Manager panel
- Display shows: "No one home"

## Working Hypothesis

In `coordinator.py`, `_last_present_persons` is only populated during `_evaluate_time_program_presences()`. When `global_mode == MODE_TIME_PROGRAM`, `_evaluate_time_program()` is called instead, which explicitly sets `_last_present_persons = []`. This zero-resets the list regardless of what persons have configured in their `mode` field.

The status should reflect configured person presence regardless of global mode (the mode only affects whether presence influences TRV temperatures — it shouldn't hide the presence state from the UI).

## Current Focus

hypothesis: CONFIRMED — _last_present_persons always reset to [] in MODE_TIME_PROGRAM, never populated from person config
next_action: RESOLVED

## Evidence

- coordinator.py:155-159 (`_evaluate_time_program`): `self._last_present_persons = []` — hardcoded, no person evaluation
- coordinator.py:306-309 (`_evaluate_time_program_presences`): `_last_present_persons` only populated here
- coordinator.py:362-369 (`_build_status_payload`): reads `_last_present_persons` directly — stale when not in presences mode

## Eliminated

(none)

## Resolution

root_cause: `_last_present_persons` was hard-reset to `[]` in both the `MODE_OFF` block and `_evaluate_time_program()`, so person presence config was never reflected in the status payload when global mode was not `MODE_TIME_PROGRAM_PRESENCES`.
fix: Added `_compute_present_persons(config, now)` helper in `ClimateManagerCoordinator` that iterates `persons_config` and calls `resolve_presence()` on each entry. The `MODE_OFF` block and `_evaluate_time_program()` now call this helper instead of assigning `[]`. TRV control behaviour is unchanged — presence only drives temperatures in `MODE_TIME_PROGRAM_PRESENCES`.
verification: Frontend build passes. Status payload will now include all persons whose `mode == "present"` (or automatic schedule evaluates to present) regardless of global mode.
files_changed:
  - custom_components/climate_manager/coordinator.py

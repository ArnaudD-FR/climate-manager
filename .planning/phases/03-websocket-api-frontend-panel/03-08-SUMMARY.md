---
phase: 03-websocket-api-frontend-panel
plan: "08"
subsystem: backend-presence
tags: [phase-03, backend, presence, person-modes, d-21, storage-migration]
dependency_graph:
  requires: ["03-04", "03-07"]
  provides: ["PRESENCE_HA constant", "force_present/force_absent wire values", "HA-mode presence detection", "D-21 storage migration"]
  affects: ["coordinator._compute_present_persons", "storage.async_load", "const.py exports"]
tech_stack:
  added: []
  patterns: ["HA state lookup via hass.states.get(person_id)", "idempotent one-shot storage migration"]
key_files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/schedule.py
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/storage.py
    - tests/test_coordinator.py
    - tests/test_storage.py
decisions:
  - "Schedule period state literals ('present'/'absent' inside person schedule entries) are distinct from presence mode constants — schedule.py compares against literal 'present' not PRESENCE_PRESENT"
  - "Storage migration uses string literals (not const imports) — matches existing 'automatic'→'scheduled' pattern, avoids circular concern"
  - "HA-mode: only exact string 'home' qualifies as present; all other states (not_home, unknown, unavailable, zone names, None) → absent"
metrics:
  duration: "5m"
  completed_date: "2026-05-21"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 6
  new_tests: 11
---

# Phase 03 Plan 08: D-21 Presence Mode Wire Value Rename + HA Mode Summary

D-21 backend implementation: `PRESENCE_PRESENT` renamed to `"force_present"`, `PRESENCE_ABSENT` to `"force_absent"`, new `PRESENCE_HA = "ha"` constant added, storage migration applied at load time, and coordinator HA-mode branch reads `hass.states.get(person_id).state == "home"` as the presence signal.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update presence constant VALUES in const.py and add PRESENCE_HA | 0a986f7 | const.py, schedule.py, tests/test_coordinator.py |
| 2 | Update tests + add storage migration for present/absent → force_present/force_absent | 82f8d33 | storage.py, tests/test_storage.py |
| 3 | Add HA-mode branch to coordinator._compute_present_persons with test coverage | 86daa90 | coordinator.py, tests/test_coordinator.py |

## What Was Built

### New PRESENCE_HA wire value
`PRESENCE_HA = "ha"` added to `const.py` alongside the renamed `PRESENCE_PRESENT = "force_present"` and `PRESENCE_ABSENT = "force_absent"`.

### Storage migration (D-21)
`storage.async_load()` now renames stored person modes in a single for-loop:
```
"automatic" → "scheduled"  (pre-existing)
"present"   → "force_present"  (D-21)
"absent"    → "force_absent"   (D-21)
```
Idempotent: re-running on already-migrated data is a no-op.

### Coordinator HA-mode branch
`_compute_present_persons` replaced its list comprehension with an explicit for-loop:
```python
if person_config.get("mode") == PRESENCE_HA:
    state_obj = self._hass.states.get(person_id)
    if state_obj is not None and state_obj.state == "home":
        present.append(person_id)
else:
    if resolve_presence(person_config, now):
        present.append(person_id)
```
`resolve_presence()` stays pure — no `hass` parameter added.

### Test literal migration in test_coordinator.py
3 hardcoded `"mode": "present"` / `"mode": "absent"` literals migrated to `"force_present"` / `"force_absent"` (lines 294, 299, 559).

## New Tests Added (11 total)

### Storage migration tests (4)
- `test_load_migrates_present_to_force_present` — verifies "present" → "force_present"
- `test_load_migrates_absent_to_force_absent` — verifies "absent" → "force_absent"
- `test_load_already_migrated_force_present_unchanged` — idempotency check
- `test_load_unrelated_modes_unchanged` — "scheduled" and "ha" untouched

### HA-mode coordinator tests (7)
- `test_compute_present_persons_ha_mode_state_home` — state='home' → present
- `test_compute_present_persons_ha_mode_state_not_home` — state='not_home' → absent
- `test_compute_present_persons_ha_mode_state_unknown` — state='unknown' → absent
- `test_compute_present_persons_ha_mode_state_missing` — entity not found (None) → absent
- `test_compute_present_persons_ha_mode_state_unavailable` — state='unavailable' → absent
- `test_compute_present_persons_ha_mode_state_zone_name` — state='work' → absent
- `test_compute_present_persons_mixed_modes` — force_present + ha+home + ha+not_home → 2 present

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed schedule.py period state comparison after const rename**
- **Found during:** Task 1 (first test run)
- **Issue:** `resolve_presence()` compared `active_state == PRESENCE_PRESENT` where `active_state` is a periodic schedule entry state ("present"/"absent" literals from PERSON-04). After D-21 renamed `PRESENCE_PRESENT` to `"force_present"`, this comparison always returned False for scheduled persons.
- **Fix:** Changed `schedule.py` line 155 to compare `active_state == "present"` (the binary schedule state literal), not the presence mode constant. Added clarifying comment distinguishing schedule period states from mode constants.
- **Files modified:** `custom_components/climate_manager/schedule.py`
- **Commit:** 0a986f7

The plan mentioned `test_schedule.py` uses `{"mode": PRESENCE_PRESENT}` (correctly using the constant name), but `schedule.py` itself also used `PRESENCE_PRESENT` to compare against schedule `state` fields — these are different things. The fix is correct per the plan's note: "schedule period state literals...are NOT affected by D-21."

## Threat Mitigations Applied

- **T-03-08-01**: `_compute_present_persons` treats unknown modes by falling through to `resolve_presence`; `resolve_presence` defaults to `PRESENCE_AUTOMATIC` for unknown modes — malformed payload degrades to scheduled behavior.
- **T-03-08-04**: `hass.states.get(person_id)` returns `None` → treated as absent (no crash).

## Test Results

- Pre-existing tests: 50 → all still pass
- New tests: 11 added (4 storage migration + 7 HA-mode coordinator)
- Total: 78 tests, all pass

## Self-Check: PASSED

- const.py: PRESENCE_PRESENT = "force_present", PRESENCE_ABSENT = "force_absent", PRESENCE_HA = "ha" ✓
- storage.py: force_present and force_absent migration branches present ✓
- coordinator.py: PRESENCE_HA import + hass.states.get branch present ✓
- tests/test_storage.py: 4 new migration tests present ✓
- tests/test_coordinator.py: 7 new HA-mode tests + 3 migrated literals ✓
- All commits exist: 0a986f7, 82f8d33, 86daa90 ✓
- Full test suite: 78 passed ✓

---
phase: 02-backend-engines-coordinator
fixed_at: 2026-05-17T00:00:00Z
review_path: .planning/phases/02-backend-engines-coordinator/02-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-05-17T00:00:00Z
**Source review:** .planning/phases/02-backend-engines-coordinator/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (4 Critical + 4 Warning)
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: Add `__all__` to `__init__.py`

**Files modified:** `custom_components/climate_manager/__init__.py`
**Commit:** 69843d8
**Applied fix:** Added `__all__ = ["ClimateManagerData", "ClimateManagerConfigEntry", "ClimateManagerCoordinator"]` after the `ClimateManagerConfigEntry` type alias, making the public API explicit.

---

### CR-02: Guard unknown `period_mode` in `_evaluate_time_program` and `_evaluate_time_program_presences`

**Files modified:** `custom_components/climate_manager/coordinator.py`
**Commit:** 49e309f
**Applied fix:** Replaced both direct `period_temperatures[period_mode]` accesses with `.get(period_mode)`, adding a `_LOGGER.warning(...)` and `continue` when the result is `None`. Both call sites in `_evaluate_time_program` (baseline loop) and `_evaluate_time_program_presences` (Step 1 baseline loop) are fixed.

---

### CR-03: Replace `23:59:59` sentinel with `None` for end-of-day occupied window

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** 26c226a
**Applied fix:** Changed `occupied_end` to `datetime.time | None`, setting it to `None` when the last N/C period is the final period of the day. The subsequent `>= occupied_end` check is guarded with `if occupied_end is not None`, so the window correctly extends to midnight with no false positive Reduced return at 23:59:58.

---

### CR-04: Deep-merge nested dicts in storage sparse-merge

**Files modified:** `custom_components/climate_manager/storage.py`
**Commit:** f35a471
**Applied fix:** Replaced `result.update(stored)` with a loop that merges nested dicts key-by-key (`result[key].update(value)`) while replacing top-level scalar/list values wholesale. Prevents a stored partial `period_temperatures` dict from silently dropping keys not present in the stored data.

---

### WR-01: Add debug log in `evaluate_schedule` for first-match-wins group selection

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** 4639340
**Applied fix:** Added `import logging` and `_LOGGER = logging.getLogger(__name__)` at module level. Added `_LOGGER.debug("evaluate_schedule: using first matching group for today (%s)", today)` inside the matching-group branch, surfacing the silent first-match-wins behavior.

---

### WR-02: Guard unavailable/removed TRV entities in `_push_if_changed`

**Files modified:** `custom_components/climate_manager/coordinator.py`
**Commit:** 6cef9d2
**Applied fix:** Added an early-return guard at the top of `_push_if_changed` that fetches the entity state once and returns immediately if `state is None or state.state == "unavailable"`. The existing D-03 manual-override check was updated to reuse this already-fetched state, removing the redundant second `hass.states.get()` call.

---

### WR-03: Log debug message in `compute_occupied_temp` when no N/C periods found

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** 4639340
**Applied fix:** Added `_LOGGER.debug("compute_occupied_temp: no periods for today (%s) — returning Reduced for present person", today)` inside the `if not nc_periods:` branch, logging the weekday integer so operators can diagnose why a present person's room falls back to Reduced.

---

### WR-04: Add coordinator test for frost-protection before first scheduled period

**Files modified:** `tests/test_coordinator.py`
**Commit:** 6dc231b
**Applied fix:** Added `LATE_START_PROGRAM` fixture (schedule starting at 07:00, no 00:00 period) and test `test_coordinator_applies_frost_before_first_period` that freezes time at 14:00 UTC (06:00 US/Pacific, before the 07:00 first period) and asserts the coordinator pushes `DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]` (7.0°C) to the TRV.

---

## Test Results

All 56 tests passed after fixes:
```
56 passed in 1.01s
```

---

_Fixed: 2026-05-17T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

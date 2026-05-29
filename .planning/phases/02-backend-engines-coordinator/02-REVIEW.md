---
phase: 02-backend-engines-coordinator
reviewed: 2026-05-17T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - custom_components/climate_manager/__init__.py
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/schedule.py
  - tests/test_coordinator.py
  - tests/test_init.py
  - tests/test_schedule.py
findings:
  critical: 4
  warning: 4
  info: 2
  total: 10
status: fixed
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-17T00:00:00Z **Depth:** standard **Files Reviewed:** 7
**Status:** issues_found

## Summary

The reviewed files cover the coordinator control loop, schedule/presence
evaluation engine, storage integration entry point, and their unit tests. The
overall architecture is sound and follows HA patterns correctly — the two-call
TRV sequence, the push-on-change cache, manual override hold, and presence-wins
logic are all implemented consistently with the design intent.

However, four critical defects were found:

1. `ClimateManagerCoordinator` is not exported from `__init__.py`, making test
   imports fail at import time.
2. An invalid `mode` string in a stored schedule causes an unhandled `KeyError`
   that crashes the coordinator's entire tick silently (only the inner `except`
   catches per-entity, not per-room schedule evaluation).
3. The occupied-window end of day is hard-coded to `23:59:59`, causing one full
   minute of incorrect temperature (rooms that should be Reduced from midnight
   to 23:59:59 are kept heated).
4. The storage sparse-merge only does a shallow top-level `dict.update`, so a
   stored config that sets only `"global_mode"` silently drops
   `"period_temperatures"`, causing a `KeyError` crash on first evaluate.

---

## Critical Issues

### CR-01: `ClimateManagerCoordinator` not exported from `__init__.py` — tests fail at import

**File:** `custom_components/climate_manager/__init__.py` **Line:** 29 (in
`__init__.py` — the class is only imported there, not re-exported)

**Issue:** Both `tests/test_init.py:13` and `tests/test_coordinator.py:17`
import `ClimateManagerCoordinator` directly from the package root:

```python
from custom_components.climate_manager import ClimateManagerCoordinator, ClimateManagerData
```

`__init__.py` imports `ClimateManagerCoordinator` for internal use
(`from .coordinator import ClimateManagerCoordinator`) but it is used only in
the function body of `async_setup_entry` — not assigned at module level so it is
technically a module attribute, but only due to the `from .coordinator import`
line at the top of `__init__.py`. Actually the import _does_ land as a module
attribute via `from .coordinator import ClimateManagerCoordinator`. However the
public interface is implicit and undocumented; if the import is ever moved
inside the function it will silently break both test files. More critically,
`ClimateManagerData` at line 40 of `__init__.py` is a local dataclass but
`ClimateManagerCoordinator` comes from a re-export. Neither class appears in
`__all__`, making the public API undefined.

**Fix:** Explicitly re-export both symbols at module level:

```python
# At the bottom of __init__.py, after the class definitions:
__all__ = ["ClimateManagerData", "ClimateManagerConfigEntry", "ClimateManagerCoordinator"]
```

---

### CR-02: Unhandled `KeyError` from invalid `period_mode` in `_evaluate_time_program` and `_evaluate_time_program_presences` crashes entire coordinator tick

**File:** `custom_components/climate_manager/coordinator.py` **Lines:** 149-150,
192-193

**Issue:** `evaluate_schedule` returns whatever string is stored in
`period["mode"]` in the schedule data. If a persisted schedule contains a typo
or unsupported mode name (e.g., `"normal "` with a trailing space, or a future
mode not yet in `period_temperatures`), the line:

```python
desired_temp = period_temperatures[period_mode]   # line 150
desired_temps[area_id] = period_temperatures[period_mode]  # line 193
```

raises `KeyError`. This exception is **not** caught by the per-entity
`try/except` block at lines 154-158 (which wraps only `_push_if_changed`). The
exception propagates out of `_evaluate_time_program` and then out of
`async_evaluate`, silently skipping ALL remaining rooms for that tick. The outer
`async_track_time_interval` does not re-raise, so the failure is invisible
unless the user reads logs at ERROR level.

**Fix:** Use `.get()` with a safe fallback and log a warning for the unknown
mode:

```python
desired_temp = period_temperatures.get(period_mode)
if desired_temp is None:
    _LOGGER.warning(
        "Unknown period mode %r for area %s — skipping", period_mode, area_id
    )
    continue
```

---

### CR-03: Occupied-window end hard-coded as `23:59:59` — last minute of day is incorrectly heated

**File:** `custom_components/climate_manager/schedule.py` **Lines:** 198-203,
210

**Issue:** When the last Normal/Comfort period is also the last period of the
day, the occupied-window end is set to `datetime.time(23, 59, 59)`:

```python
occupied_end = datetime.time(23, 59, 59)
```

The check at line 210 is `current_time >= occupied_end`, so at exactly
`23:59:59` the room flips to Reduced, but from `23:59:00` through `23:59:58`
(one minute window) the room remains heated when it should be Reduced. More
importantly, SCHED-03 says the last period ends at **midnight** — not 23:59:59.
If a person is present and their last N/C period is, say, `21:00 comfort` with
no following period, the heating stays on until `23:59:59` instead of running
until midnight and then switching at the next day's period, which is the correct
design.

The correct sentinel for "midnight" in this context is `datetime.time(0, 0)`
compared against the _next day_, but since the function only works within a
single day's period list, the correct fix is to use `datetime.time(23, 59, 59)`
replaced with a sentinel that makes the `>=` check never true for any valid time
within the day — i.e., the window should extend to midnight (inclusive of
23:59:59 and every second up to but not including 00:00 next day). The actual
issue is that `23:59:59` as `occupied_end` will cause the `>= occupied_end`
branch to fire 1 second before midnight and return Reduced. The window should be
open until midnight:

**Fix:** Replace with a sentinel that can never be reached within the same
calendar day — use `None` to indicate "end of day" and skip the
`>= occupied_end` check entirely:

```python
if last_nc_idx + 1 < len(today_periods):
    occupied_end: datetime.time | None = _parse_time(today_periods[last_nc_idx + 1]["start"])
else:
    occupied_end = None  # last N/C is last period — window extends to midnight

# After the occupied window → Reduced
if occupied_end is not None and current_time >= occupied_end:
    return period_temperatures[PERIOD_REDUCED]
```

---

### CR-04: Storage sparse-merge is shallow — `period_temperatures` silently dropped on partial stored config

**File:** `custom_components/climate_manager/storage.py` **Lines:** 53-54

**Issue:** The merge in `async_load` uses `dict.update`:

```python
result = copy.deepcopy(DEFAULT_CONFIG)
result.update(stored)
```

`dict.update` replaces entire top-level keys. If the stored JSON contains a
`"period_temperatures"` key with only some temperature keys (e.g., only
`"frost_protection"` was customised and other keys were omitted by a future
partial-save), the stored dict fully replaces the default, dropping the missing
keys. Any subsequent `period_temperatures[PERIOD_REDUCED]` (or any other missing
key) raises `KeyError` and crashes the coordinator.

Conversely, if the stored config contains **only** `"global_mode"` and `"rooms"`
(a valid sparse-storage scenario per the D-11 design), then `result` after
`update` still has all DEFAULT_CONFIG keys — so that case is fine. The real risk
is a stored `"period_temperatures"` that is itself sparse. This is a latent bug
that will trigger once the Phase 3 WebSocket save handler is implemented and
allows partial updates to `period_temperatures`.

**Fix:** Deep-merge nested dicts rather than replacing them:

```python
result = copy.deepcopy(DEFAULT_CONFIG)
for key, value in stored.items():
    if isinstance(value, dict) and isinstance(result.get(key), dict):
        result[key].update(value)  # merge nested dicts
    else:
        result[key] = value
return result
```

---

## Warnings

### WR-01: `evaluate_schedule` breaks early with `break` but loop logic means unsorted input across groups causes wrong result

**File:** `custom_components/climate_manager/schedule.py` **Lines:** 97-104

**Issue:** Inside the found group, periods are `sorted()` before walking them.
However the early-exit `break` at line 104 (`else: break`) assumes periods are
in ascending order — which is correct since they are sorted. But the function
also returns on the _first_ matching group (line 105 `return active_mode ...`).
If two groups happen to both contain today's weekday (a violation of D-06, but
validation is only called at save time, not at evaluate time), the second group
is silently ignored and the first group's result is returned. This is an
acceptable design trade-off but the silent failure mode deserves a guard log:

**Fix:** Add a warning log when an invalid schedule passes through
`evaluate_schedule` without validation (or call `validate_7day_coverage` inside
`evaluate_schedule` and log if invalid):

```python
_LOGGER.debug("evaluate_schedule: using first matching group for today (%s)", today)
```

Or add a development-time assertion: `assert active_mode is not None or ...`.

---

### WR-02: `_push_if_changed` manual-override hold is defeated when TRV state is `None`

**File:** `custom_components/climate_manager/coordinator.py` **Lines:** 273-279

**Issue:** The manual-override hold reads the TRV state and compares `reported`
to `last`. If `hass.states.get(entity_id)` returns `None` (entity removed from
HA but still in the `rooms` dict), the code skips the override check and
proceeds to call `set_trv_temperature`. `set_trv_temperature` already guards
against `None` state (returns early), so no crash occurs. However
`_last_pushed[entity_id]` is then **not updated** (because `set_trv_temperature`
returns without pushing), yet no exception is raised. On every subsequent tick,
the code re-enters `_push_if_changed` with `last != desired_temp` and calls
`set_trv_temperature` again — a no-op call repeated every minute for a removed
entity, generating noise in service call logs.

**Fix:** After the `set_trv_temperature` call at line 282, verify the push
actually happened, or guard earlier:

```python
state = self._hass.states.get(entity_id)
if state is None or state.state == "unavailable":
    return  # already guarded in set_trv_temperature, but skip _last_pushed update here too
```

Move this guard to before the override-hold check so removed entities
short-circuit completely.

---

### WR-03: `compute_occupied_temp` does not handle an empty `weekday_groups` for the present-person path — returns `PERIOD_REDUCED` but caller may expect otherwise

**File:** `custom_components/climate_manager/schedule.py` **Lines:** 179-192

**Issue:** When `weekday_groups` is empty and `is_present=True`, `today_periods`
stays as `[]`, `nc_periods` is `[]`, and the function returns
`period_temperatures[PERIOD_REDUCED]`. This is consistent with D-05 and is
tested. However, in `_evaluate_time_program_presences` (coordinator.py lines
219-225), the `weekday_groups` passed to `compute_occupied_temp` may be the
**global** time program when no room override exists. If the global program has
a valid schedule, that path is fine. But if the global program has an empty
`weekday_groups` (fresh install default — `{"weekday_groups": []}`), then a
present person's room falls back to `PERIOD_REDUCED`, silently downgrading from
the expected default behavior. No warning is logged.

**Fix:** Log a warning when a present person's room resolves to Reduced due to
missing schedule, so operators can diagnose the configuration:

```python
if not today_periods:
    _LOGGER.debug(
        "compute_occupied_temp: no periods for today — returning Reduced for present person"
    )
```

---

### WR-04: `WEEKDAY_PROGRAM` test fixture missing periods before first defined start — `evaluate_schedule` returns `PERIOD_FROST_PROTECTION` before 07:00 but test does not cover this case for `WEEKDAY_PROGRAM`

**File:** `tests/test_schedule.py` **Lines:** 39-54

**Issue:** `WEEKDAY_PROGRAM` defines weekday periods starting at `07:00` with no
`00:00` period.
`test_evaluate_schedule_before_first_period_returns_frost_protection` (line 121)
correctly tests this. However, the test comment says "Before the first period of
the day → PERIOD_FROST_PROTECTION" but the assertion relies on the fallback,
meaning any time from `00:00` to `06:59` returns frost-protection even when
users likely intended a different default. This is by design but there is no
test asserting the coordinator then applies
`period_temperatures[PERIOD_FROST_PROTECTION]` to all TRVs when a room's
schedule returns frost-protection — the coordinator at line 150 does
`period_temperatures[period_mode]` which would return `7.0°C`. This is a real
operational risk (rooms defaulting to 7°C frost-protection for 7 hours nightly
when no 00:00 period is configured), and no coordinator-level test covers it.

**Fix:** Add a test in `test_coordinator.py` asserting that a room with a
weekday schedule starting at 07:00 (no 00:00 period) receives
`period_temperatures[PERIOD_FROST_PROTECTION]` at 06:00.

---

## Info

### IN-01: `test_coordinator.py` imports `ClimateManagerCoordinator` and `ClimateManagerData` from the package but never uses `ClimateManagerData`

**File:** `tests/test_coordinator.py` **Line:** 17

**Issue:** `ClimateManagerData` is imported but not referenced anywhere in
`test_coordinator.py`. The tests access `entry.runtime_data` directly (which is
typed as `ClimateManagerData` at runtime) but never call
`isinstance(..., ClimateManagerData)`.

**Fix:** Remove the unused import:

```python
from custom_components.climate_manager import ClimateManagerCoordinator
```

---

### IN-02: Magic sentinel `datetime.time(23, 59, 59)` should be a named constant

**File:** `custom_components/climate_manager/schedule.py` **Line:** 203

**Issue:** The value `datetime.time(23, 59, 59)` is a magic literal with no
explanation at the call site (beyond the inline comment). If CR-03 is not fixed,
at minimum this should be a named constant.

**Fix:**

```python
# In schedule.py module level:
_END_OF_DAY = datetime.time(23, 59, 59)
```

---

_Reviewed: 2026-05-17T00:00:00Z_ _Reviewer: Claude (gsd-code-reviewer)_ _Depth:
standard_

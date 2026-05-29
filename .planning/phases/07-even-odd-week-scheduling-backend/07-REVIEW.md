---
phase: 07-even-odd-week-scheduling-backend
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - custom_components/climate_manager/schedule.py
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/websocket.py
  - frontend/src/types.ts
  - tests/test_schedule.py
  - tests/test_websocket.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-29
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This phase adds even/odd ISO-week schedule selection for persons. The core
even/odd dispatch logic in `schedule.py` and the seeding logic in
`websocket.py` are implemented correctly and the tests are thorough. However,
a pre-existing but now more-exposed bug is confirmed: **all three schedule
evaluation functions sort periods by their raw `"start"` string** rather than
by the parsed `datetime.time` value. This produces a silently incorrect active
period whenever a time is not zero-padded (e.g. `"9:30"` instead of
`"09:30"`). A separate structural concern is that `validate_daily_program`
validates only day-key presence, leaving period structure entirely unvalidated,
so the sort bug can be triggered by any frontend or test that omits zero
padding.

One additional correctness issue: `compute_occupied_temp` finds the position
of the last Normal/Comfort period via `list.index()`, which returns the
position of the **first** dict equal to the target. With duplicate
`{start, mode}` period entries the wrong `occupied_end` is computed.

---

## Critical Issues

### CR-01: Lexicographic string sort for period start times produces wrong active period

**File:** `custom_components/climate_manager/schedule.py:106, 155, 193`

**Issue:** All three evaluation functions sort the period list using the raw
`"start"` string as the key:

```python
sorted_periods = sorted(periods, key=lambda p: p["start"])
```

Python string comparison is lexicographic: `"10:00" < "9:00"` because `"1" <
"9"` in ASCII. Any period whose start hour is a single digit without
zero-padding (e.g. `"9:30"`) will sort **after** all two-digit-hour times,
making the active-period selection wrong.

Concretely: if a user or a future frontend sends `{"start": "9:00",
"mode": "normal"}`, that period will sort after `"22:00"` and will never be
selected as active, while `_parse_time("9:00")` correctly produces
`datetime.time(9, 0)` — so the comparison itself is fine once the sort order
is fixed.

`validate_daily_program` does not validate period structure (only day keys),
so non-zero-padded times are accepted and silently corrupt evaluation.

**Fix:** Sort by the parsed `datetime.time` object, not the raw string, in all
three evaluation functions:

```python
# evaluate_schedule (line 106) — and same change in resolve_presence (155)
# and compute_occupied_temp (193-194)
sorted_periods = sorted(
    periods, key=lambda p: _parse_time(p["start"])
)
```

This requires `_parse_time` to be called at sort time (it is a pure function
with no side effects). As a complementary defence, `validate_daily_program`
should also reject non-`HH:MM` period starts — see WR-01 below.

---

## Warnings

### WR-01: `validate_daily_program` does not validate period structure

**File:** `custom_components/climate_manager/schedule.py:255-277`

**Issue:** `validate_daily_program` only checks that all seven day keys are
present and no unknown day keys exist. It does not validate:
- Each period has a `"start"` key.
- `"start"` is a zero-padded `"HH:MM"` string (reachable via test suite or a
  buggy frontend).
- Each period has a `"mode"` (or `"state"`) key.
- No two periods share the same start time within a day.

As a result, a program like `{"mon": [{"mode": "normal"}], ...}` passes
validation but causes `KeyError: 'start'` at evaluation time, crashing the
schedule engine.

**Fix:** Add period-level validation:

```python
import re
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

def validate_daily_program(daily_program):
    ...  # existing day-key checks ...
    for day, periods in daily_program.items():
        if day not in ALL_DAYS:
            continue
        starts_seen = set()
        for i, period in enumerate(periods):
            if "start" not in period:
                return False, f"{day}[{i}]: missing 'start' key"
            if not _TIME_RE.match(period["start"]):
                return False, (
                    f"{day}[{i}]: 'start' must be HH:MM (zero-padded), "
                    f"got {period['start']!r}"
                )
            if period["start"] in starts_seen:
                return False, f"{day}[{i}]: duplicate start time {period['start']!r}"
            starts_seen.add(period["start"])
            if "mode" not in period and "state" not in period:
                return False, f"{day}[{i}]: period must have 'mode' or 'state'"
    return True, ""
```

---

### WR-02: `compute_occupied_temp` uses `list.index()` to locate last N/C period — returns wrong index on duplicate dicts

**File:** `custom_components/climate_manager/schedule.py:215`

**Issue:**

```python
last_nc_idx = today_periods.index(nc_periods[-1])
```

`list.index()` returns the index of the **first** element that compares equal
to the target. If two periods share identical `{"start": ..., "mode": ...}`
values (e.g. two `{"start": "07:00", "mode": "normal"}` entries — possible
since duplicate start times are not rejected by validation), the wrong position
is returned and `occupied_end` is computed from the period immediately after the
**first** N/C period instead of the last, causing the gap-fill window to be
truncated.

**Fix:** Replace `index()` with an identity-based search or find by position
directly from the filtered list:

```python
# Find the position of nc_periods[-1] by identity, not equality
last_nc_idx = next(
    i for i, p in enumerate(today_periods) if p is nc_periods[-1]
)
```

This works because `nc_periods` is built by filtering `today_periods` with a
list comprehension, preserving object identity. Alternatively, track indices
during the N/C filter:

```python
nc_period_indices = [
    i for i, p in enumerate(today_periods) if p["mode"] in nc_modes
]
last_nc_idx = nc_period_indices[-1]
```

---

### WR-03: Even/odd week parity breaks for two consecutive weeks at 53-week year boundaries

**File:** `custom_components/climate_manager/schedule.py:141-143`

**Issue:**

```python
week_parity = now.date().isocalendar().week % 2
schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
```

In years that contain ISO week 53 (e.g. 2026), week 53 has parity `1`
(odd). The immediately following week 1 of the next year **also** has parity
`1` (odd). A user who intends an alternating even/odd pattern therefore
experiences **two consecutive "odd" weeks** at the year boundary, skipping one
"even" week entirely. This happens in 2026–2027 and in any subsequent 53-week
year.

There is no documentation, UI warning, or parity-correction in the code.

**Fix options (in increasing complexity):**

1. **Document the known limitation** in `schedule.py` and in the user-facing
   UI so users are not surprised.
2. **Shift to a fixed reference point**: define week parity relative to a
   fixed anchor date (e.g. ISO week 1 of 2024) rather than the raw week
   number modulo 2. This preserves strict alternation across all year
   boundaries:

```python
# Anchor: ISO week 1 of 2024 is "even" (0)
ANCHOR_YEAR = 2024
anchor = datetime.date(ANCHOR_YEAR, 1, 8)  # first Monday of 2024
week_delta = (
    now.date().isocalendar().year * 53 + now.date().isocalendar().week
    - anchor.isocalendar().year * 53 - anchor.isocalendar().week
)
schedule_key = "schedule_even" if week_delta % 2 == 0 else "schedule_odd"
```

---

## Info

### IN-01: `PRESENCE_HA` ("ha") mode falls through silently to schedule evaluation in `resolve_presence`

**File:** `custom_components/climate_manager/schedule.py:131-165`

**Issue:** `resolve_presence` explicitly handles `PRESENCE_PRESENT` and
`PRESENCE_ABSENT` then falls through for all other values, including
`PRESENCE_HA` ("ha"). An "ha" mode person passed directly to `resolve_presence`
will be evaluated as "automatic" against a schedule, which is semantically
wrong.

The coordinator (`coordinator.py:321`) guards against this by handling "ha"
mode before calling `resolve_presence`, so there is no runtime bug in the main
path. However the function's contract is silent about unrecognised modes, and
any future caller that bypasses the coordinator guard will get wrong results
without any error.

**Fix:** Add an explicit guard or docstring clarification:

```python
# Explicit: unrecognised modes (including PRESENCE_HA) are delegated
# to schedule evaluation. Callers must handle PRESENCE_HA separately
# before calling this function.
```

Or assert/log:

```python
if mode not in (PRESENCE_PRESENT, PRESENCE_ABSENT, PRESENCE_AUTOMATIC):
    _LOGGER.warning(
        "resolve_presence: unrecognised mode %r for %s — "
        "falling back to automatic schedule evaluation",
        mode, person_config,
    )
```

---

### IN-02: `validate_daily_program` error message uses `sorted(missing)` producing non-deterministic set ordering prior to sort — minor cosmetic concern

**File:** `custom_components/climate_manager/schedule.py:273-276`

**Issue:** `missing` and `extra` are `set` objects. `sorted()` is called
before formatting, which correctly produces a deterministic sorted list. This
is fine. However, the resulting error string like `"Missing days:
['sun']"` formats the list with brackets and quotes, producing a slightly
unusual user-facing error (e.g. `"Missing days: ['fri', 'sun']"` rather than
`"Missing days: fri, sun"`).

**Fix:**

```python
parts.append(f"Missing days: {', '.join(sorted(missing))}")
parts.append(f"Unknown days: {', '.join(sorted(extra))}")
```

---

_Reviewed: 2026-05-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

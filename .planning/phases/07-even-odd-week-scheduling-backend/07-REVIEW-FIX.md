---
phase: 07-even-odd-week-scheduling-backend
fixed_at: 2026-05-29T00:00:00Z
review_path: .planning/phases/07-even-odd-week-scheduling-backend/07-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-05-29
**Source review:** .planning/phases/07-even-odd-week-scheduling-backend/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (1 Critical + 3 Warning)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Lexicographic string sort for period start times produces wrong active period

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** 910aa12
**Applied fix:** Changed all three `sorted(periods, key=lambda p: p["start"])` calls
to use `_parse_time(p["start"])` as the sort key. The three affected sites are
`evaluate_schedule` (line 106), `resolve_presence` (line 155), and
`compute_occupied_temp` (lines 193-195). This ensures chronological sort order
regardless of whether period start strings are zero-padded.

---

### WR-01: `validate_daily_program` does not validate period structure

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** 5f80dd0
**Applied fix:** Added `import re` and a module-level `_TIME_RE` compiled regex
(`^([01]\d|2[0-3]):[0-5]\d$`). Extended `validate_daily_program` with a
period-level validation loop that rejects: missing `"start"` key, non-zero-padded
time strings, duplicate start times within a day, and periods missing both
`"mode"` and `"state"` keys. Also improved error message formatting from
`str(sorted_list)` repr to comma-joined strings (e.g. `"fri, sun"` not
`"['fri', 'sun']"`).

---

### WR-02: `compute_occupied_temp` uses `list.index()` — returns wrong index on duplicate dicts

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** c1a9f8e
**Applied fix:** Replaced `today_periods.index(nc_periods[-1])` with an
identity-based search using `next(i for i, p in enumerate(today_periods) if p is
nc_periods[-1])`. This is correct because `nc_periods` is built by filtering
`today_periods` via list comprehension, so object identity is preserved. Duplicate
period dicts no longer cause the wrong `last_nc_idx` to be selected.

---

### WR-03: Even/odd week parity breaks at ISO 53-week year boundaries

**Files modified:** `custom_components/climate_manager/schedule.py`
**Commit:** 71ae703
**Applied fix:** Added an inline comment block inside the `schedule_type ==
"even_odd"` branch documenting the known limitation: raw ISO week number modulo 2
produces two consecutive odd weeks at 53-week year boundaries (e.g. 2026-2027).
The comment notes this is an accepted v1 limitation and hints at the anchor-date
approach for a future fix. No code behavior change — this is a documentation
caveat fix as agreed per additional context.

---

## Skipped Issues

None — all findings were fixed.

---

_Fixed: 2026-05-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

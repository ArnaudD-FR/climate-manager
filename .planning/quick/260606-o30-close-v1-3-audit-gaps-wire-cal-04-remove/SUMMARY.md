---
quick_id: 260606-o30
title: Close v1.3 audit gaps (CAL-04 + UI drift)
status: complete
date: 2026-06-06
requirements-completed: [CAL-04, UI-01, UI-02]
---

# Quick Task 260606-o30: Close v1.3 audit gaps — Summary

Closed the two substantive findings from `.planning/v1.3-MILESTONE-AUDIT.md`
before completing the v1.3 milestone.

## CAL-04 — wakeup_advance_minutes now functional

`resolve_calendar_presence` previously ignored `preheat_lead_minutes`
(docstring: "Reserved... Currently unused"). Added `_active_window_end()` to
`schedule.py`, which computes the moment the active calendar window ends
(when the person returns home) for each `gap_handling`:

- **exact**: end of the event containing `now` (touching/overlapping events
  merged).
- **day_span**: the last event's end.
- **threshold**: the end of the contiguous run of events joined by gaps ≤
  threshold.

`resolve_calendar_presence` now flips a calendar-absent person to **present**
once that window-end falls within `preheat_lead_minutes`, so the zone schedule
applies and rooms pre-heat ahead of the return. `lead=0` disables it; no
effect when `event_means="present"`. A single change point covers both
top-level Calendar mode and per-period calendar (both route through this
function).

Tests: repurposed the two that asserted the old no-op
(`test_absent_for_full_event_duration` → `test_absent_deep_in_event_beyond_lead`;
`test_gap_threshold_in_event_always_absent` pinned to `lead=0`), added 5 CAL-04
tests (within-lead, exact boundary, lead=0 disables, present-means unaffected,
day_span window-end). **Full suite: 287 passed** (was 282).

## UI-01 / UI-02 — spec reconciled with shipped design

The shipped design (quick task 260601-d04 + memory ha-mode-rename) always shows
the HA option with a "⚠" suffix + stuck-mode hint when no device trackers
exist, and labels it "HA home tracking" — not the originally specced "hide the
option" / "Live tracking".

- Removed the dead `shouldShowHaOption` helper (always returned `true`,
  referenced only by its own test, already tree-shaken from `panel.js` —
  rebuild confirmed the bundle is byte-identical). Dropped its two tests +
  import. presence-mode node tests: 11 passed.
- Rewrote `REQUIREMENTS.md` UI-01/UI-02 to the shipped design and checked them
  off.

## Verification

- `pytest` — 287 passed.
- `node --test presence-mode.test.ts` — 11 passed.
- `make build` — clean; `panel.js` unchanged (188.20 kB).

## Commits

- `36a5d03` — fix(calendar): wire wakeup_advance_minutes (CAL-04)
- `7f9737f` — refactor(presence-mode): remove dead helper; align UI-01/02 spec

## Files

- `custom_components/climate_manager/schedule.py`
- `tests/test_calendar.py`
- `frontend/src/components/presence-mode.ts`
- `frontend/src/components/presence-mode.test.ts`
- `.planning/REQUIREMENTS.md`

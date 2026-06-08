---
slug: time-bar-delete-first-period
status: resolved
trigger: manual
created: 2026-06-08
---

# Debug: Deleting first period changes its state instead of removing it

## Symptoms

- BEFORE: Monday shows `Absent | Absent | Present` (3 blocks)
- AFTER delete on first block: Monday shows `Present | Absent | Present`
  (still 3 blocks — first block changed state, not removed)

The first block went from "Absent" to "Present" instead of disappearing.

## Evidence

- timestamp: 2026-06-08T00:00:00
  file: frontend/src/components/time-bar.ts
  finding: >
    _onDeleteSegment filters this.days[dayIndex] by p.start !==
    seg.period.start. When the deleted period has start "00:00",
    the filter removes the explicit 00:00 entry and emits the
    remaining periods (all starting after 00:00).

- timestamp: 2026-06-08T00:01:00
  file: frontend/src/components/time-bar.ts
  finding: >
    _toSegments (line 452-456) synthesises a new 00:00 entry when
    firstMin > 0 — copying the mode/state of whatever is now first.
    This means after delete the 00:00 gap is silently filled, producing
    the same number of visual segments. The first block shows the second
    period's state, which is the symptom.

## Root Cause

`_onDeleteSegment` removes the explicit `start:"00:00"` entry from
`this.days[dayIndex]`. The remaining periods all start after 00:00.
`_toSegments` then synthesises a filler `{ start:"00:00", state/mode:
<next-period-value> }` at render time, so the display still shows N blocks.
The first block "changes state" because it now reflects the second period.

The root is a data/render contract mismatch: the emitted data has a gap at
00:00 which `_toSegments` silently fills, but the parent stores the gapped
data. Next render cycle the synthesised filler is not in storage — but
`_toSegments` recreates it every time, so the UI always looks wrong (N
blocks instead of N-1).

## Fix

When `_onDeleteSegment` removes a period whose `start === "00:00"`, and
the remaining array has a new first period not at "00:00", promote that
first period to `start:"00:00"`. This makes the data and the render agree:
the schedule explicitly starts at 00:00 with the second period's type, and
the old first block disappears.

Applied to: `_onDeleteSegment` in `frontend/src/components/time-bar.ts`
(lines 659-673).

## Resolution

- root_cause: >
    _onDeleteSegment removed the 00:00 period from the data array but did
    not promote the next period to 00:00. _toSegments synthesised a filler
    from the next period's state, keeping N blocks visually while the data
    had a 00:00 gap.
- fix: >
    After filtering, when the deleted period had start "00:00", update the
    new first period's start to "00:00" before emitting. Verified with
    make build (success).
- files_changed:
    - frontend/src/components/time-bar.ts
    - custom_components/climate_manager/www/panel.js

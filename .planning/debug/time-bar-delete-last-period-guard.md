---
slug: time-bar-delete-last-period-guard
status: resolved
trigger: feature-guard
goal: find_and_fix
---

## Symptoms

In the time-bar edit popup, the Delete button is always enabled even when the
day has only one period remaining. Deleting the last period would leave the day
in an invalid empty state.

## Current Focus

hypothesis: The delete button in the edit popup has no guard on period count.
next_action: Add disabled state to Delete button when day has exactly 1 period.

## Evidence

- timestamp: 2026-06-08
  source: code-review
  note: >
    Line 1207 in time-bar.ts renders the Delete button with no disabled
    condition. The Split period button (line 1199) already uses the
    `?disabled` pattern and opacity style — the same pattern should apply
    to Delete when `this.days[this._popup.dayIndex].length === 1`.

## Resolution

root_cause: >
  The Delete button in the edit popup template (time-bar.ts ~L1207) has no
  guard based on period count. A day must always have at least one period, so
  deleting the sole remaining period would corrupt the schedule state.

fix: >
  Add `?disabled` and `style` bindings to the Delete button that check
  `this.days[this._popup.dayIndex].length === 1`. When true, the button is
  greyed out and non-clickable, matching the existing Split period button
  pattern. The `_onDeleteSegment` guard remains as defence-in-depth.

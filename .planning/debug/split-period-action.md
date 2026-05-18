---
slug: split-period-action
status: in_progress
trigger: feature_request
created: 2026-05-18
---

# Debug/Feature: Split Period Action

## Symptoms

The edit popup shown when clicking a time period segment contains a "Delete period" button but no "Split period" button. Users need to be able to split a period at its midpoint directly from the popup.

## Current Focus

**hypothesis:** The `_renderPopup()` method's `"edit"` branch renders only a delete action. A `_onSplitPeriod()` handler and a "Split" button need to be added.

**next_action:** Implement `_onSplitPeriod(dayIndex, segIndex)` in `time-bar.ts`, add a "Split" button to the edit popup HTML, and build.

## Evidence

- `frontend/src/components/time-bar.ts` — component under modification
- Snapping granularity: 15 minutes (`_snapToMinutes` rounds to nearest 15)
- Period type cycles:
  - schedule: frost_protection → reduced → normal → comfort → frost_protection
  - presence: present → absent → present
- Period data: `{ start: "HH:MM", mode?: string, state?: string }`
- End of a period = start of next period, or 1440 for the last one
- Delete handler at line 575; popup render at line 914; edit branch at line 940
- `_emitChange(dayIndex, periods)` is the emit helper

## Resolution

root_cause: Edit popup has no "Split period" action.
fix: Added `_onSplitPeriod` method and "Split" button to the popup, with type cycling and 15-min snapped midpoint.

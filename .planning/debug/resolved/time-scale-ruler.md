---
slug: time-scale-ruler
status: resolved
trigger: feature_request
created: 2026-05-18
---

# Debug / Feature Session: time-scale-ruler

## Symptoms / Goal

Add a horizontal time ruler above the 7 day-rows in `ClimateManagerTimeBar`.

The ruler should:
- Span the same width as the period bars (offset by the 40px day-label column)
- Show tick marks + labels at every 3 hours: 0, 3, 6, 9, 12, 15, 18, 21, 24
- Use `position: absolute; left: X%` ticks (X = hour/24 * 100)
- Style with HA CSS variables: `--secondary-text-color`, `--divider-color`
- Height ~18px, font-size 10px
- Be placed just before the day rows in the main render template

## Current Focus

hypothesis: The component has a `.week-grid` flex-column container. Day rows include a
40px `.day-label` + flex `.bar-wrap` + `.day-actions` buttons. The existing bottom
`.time-axis` uses `padding-left: 48px` and `padding-right: 80px` to align with bars.
The ruler must use the same horizontal offsets.

next_action: Implement `_renderTimeScale()` and insert it before the day rows.

## Evidence

- timestamp: 2026-05-18T00:00:00Z
  file: frontend/src/components/time-bar.ts
  note: >
    Layout confirmed. `.day-label` is 40px wide with 8px right padding (total 48px
    before bar). `.day-actions` is flex-shrink:0 with two ha-icon-buttons (~80px).
    Existing `.time-axis` already accounts for these with padding-left:48px and
    padding-right:80px. Ruler will mirror that approach but use absolute-positioned
    ticks over a relative container for precise alignment.

## Resolution

root_cause: No time scale existed above the period bars.
fix: Added `_renderTimeScale()` method with 9 ticks (hours 0,3,6,9,12,15,18,21,24)
     using absolute positioning. Inserted call before day rows in `render()`.

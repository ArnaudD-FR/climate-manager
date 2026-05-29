---
slug: drag-tooltip-position
status: resolved
trigger: manual
goal: find_and_fix
created: 2026-05-18
---

# Debug Session: drag-tooltip-position

## Symptoms

When dragging a time period border to change its start time, the time tip
(tooltip showing "HH:MM") is not displayed next to the mouse cursor. Instead it
appears at the bottom-left of the week days period rows.

## Current Focus

**hypothesis:** The `.drag-tooltip` element is rendered with `position: fixed`
in CSS, which is correct for viewport-relative positioning. However no
`left`/`top` style is being set on the tooltip element during drag — meaning it
defaults to `left: 0; top: 0` (top-left corner of the viewport). The
`_onPointerMove` handler only updates `_dragTooltipMinutes` (the time value),
but never stores or applies the mouse coordinates (`e.clientX`, `e.clientY`) to
position the tooltip element.

**next_action:** Add `_dragTooltipX` and `_dragTooltipY` state fields, update
them in `_onPointerMove`, and bind them as inline `style` on the `.drag-tooltip`
div.

## Evidence

- timestamp: 2026-05-18T00:00:00Z file: frontend/src/components/time-bar.ts
  finding: | CSS for `.drag-tooltip` uses `position: fixed` (line 214) which is
  correct. The tooltip is rendered at lines 658-662 with no `style` attribute —
  so it lands at left:0, top:0 (viewport top-left, or component default).
  `_onPointerMove` (lines 552-565) updates only `_dragTooltipMinutes`; it never
  captures `e.clientX` / `e.clientY` for tooltip placement. Result: tooltip
  always stays at the origin position of the fixed container (effectively the
  bottom-left area of the shadow component's stacking context, which appears as
  "bottom-left of week days periods").

## Resolution

**root_cause:** `_onPointerMove` does not track mouse coordinates for tooltip
placement. The `.drag-tooltip` element has `position: fixed` in CSS but no
`left`/`top` style is applied, so it renders at `0, 0`.

**fix:** Add two `@state` fields `_dragTooltipX` and `_dragTooltipY`. Assign
them from `e.clientX` and `e.clientY` in `_onPointerMove`. Bind
`style="left:${x}px;top:${y}px"` on the `.drag-tooltip` element. The existing
`transform: translate(-50%, -130%)` will offset the tooltip above and centred on
the cursor correctly.

**status:** applied

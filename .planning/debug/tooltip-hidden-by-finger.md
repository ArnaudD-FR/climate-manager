---
slug: tooltip-hidden-by-finger
status: resolved
trigger: "on android, dragging time period show the tooltip with new timestamp just above finger so it is hidden by finger"
created: 2026-05-26
resolved: 2026-05-26
---

# Debug Session: tooltip-hidden-by-finger

## Symptoms

- **Expected:** During drag, the time tooltip shows the current boundary time clearly visible above the finger — not obscured.
- **Actual:** The tooltip appears just above the fingertip, hidden behind the finger itself.
- **Scope:** Android touch only (on desktop the mouse cursor is small, tooltip offset is fine).
- **Reproduction:** Drag a period boundary on Android — the tooltip is visible on desktop but hidden by the finger on mobile.

## Current Focus

**hypothesis:** The tooltip is positioned using `clientY - someSmallOffset`. On desktop the cursor is ~1px so a small upward offset is enough. On Android, a finger covers ~40-60px of screen, so the tooltip needs to be offset by at least 60-80px above the touch point to clear the fingertip. The current offset is likely too small (designed for mouse cursor, not touch).

**next_action:** RESOLVED — fix applied.

## Evidence

- timestamp: 2026-05-26
  finding: |
    In `_onPointerMove` and `_onDragHandlePointerDown`, `_dragTooltipY` is set
    directly to `e.clientY`. The `.drag-tooltip` CSS uses
    `transform: translate(-50%, -130%)` which shifts the tooltip ~23px upward
    (130% of an ~18px box). That is enough for a 1px mouse cursor but not for a
    finger covering 40-60px.

## Resolution

**root_cause:** `_dragTooltipY` is set to raw `e.clientY` in both
`_onDragHandlePointerDown` and `_onPointerMove`. The CSS `transform:
translate(-50%, -130%)` only clears the pointer by ~23px — insufficient for a
touch finger (~40-60px wide). No touch-vs-mouse distinction existed.

**fix:** Added private helper `_touchTooltipOffset(e: PointerEvent): number`
that returns 60 for touch events and 0 for mouse/pen. Applied in both
`_onDragHandlePointerDown` and `_onPointerMove` as
`e.clientY - this._touchTooltipOffset(e)`. Combined with the existing CSS
transform, the tooltip now clears the fingertip by ~83px on Android touch while
desktop behaviour is unchanged.

**file:** `frontend/src/components/time-bar.ts` — lines 395-397 (helper), 734, 754 (call sites).

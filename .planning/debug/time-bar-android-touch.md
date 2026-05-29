---
slug: time-bar-android-touch
status: resolved
trigger:
  "time bar does not work on Android, it is very difficult to resize a period
  with fingers"
created: 2026-05-26
resolved: 2026-05-26
---

# Debug Session: time-bar-android-touch

## Symptoms

- **Expected:** Same as desktop — drag handle appears on touch, boundary moves
  with finger in real-time, releasing commits the change cleanly.
- **Actual:** Two combined problems:
  1. Handle too small to grab with a finger (touch target too narrow)
  2. Drag doesn't track finger — boundary jumps or doesn't move after grab
- **Scope:** Tap interactions work fine (popup opens). Only drag/resize is
  broken.
- **Reproduction:** Open time-bar on Android (HA mobile app or browser), try to
  drag a period boundary.

## Resolution

**root_cause:** Three compounding issues in
`frontend/src/components/time-bar.ts`:

1. `.drag-handle` was 6px wide (`right: -3px`) — far too small for a fingertip
   (minimum 44px per touch target guidelines)
2. `touch-action: none` was absent on `.drag-handle` — Android intercepted
   horizontal touch moves as scroll gestures, cancelling the pointer stream
   before the drag could begin
3. `pointercancel` was not handled — when Android cancelled the pointer (instead
   of firing `pointerup`), `_drag` state was never cleared, leaving the
   component stuck

**fix:** Three changes to `frontend/src/components/time-bar.ts`:

1. Widened `.drag-handle` to `width: 44px; right: -22px` (centered on boundary,
   44px touch target)
2. Added `touch-action: none` to `.drag-handle` CSS rule
3. Added `_onPointerCancel` method and bound `@pointercancel` on the week-grid
   div to clean up drag state on Android pointer cancellation

## Evidence

- Reviewed full source of `frontend/src/components/time-bar.ts`
- `setPointerCapture` was already called in `_onDragHandlePointerDown` — pointer
  tracking was architecturally correct; the drag simply never survived long
  enough to benefit from it
- `@pointermove` / `@pointerup` on the week-grid div are correct patterns for
  pointer-captured drags

## Current Focus

**hypothesis:** resolved **next_action:** none — fix applied

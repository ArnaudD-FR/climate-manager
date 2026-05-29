---
slug: time-bar-android-touch-2
status: resolved
trigger: "time bar still does not work on android — drag never starts after previous fix"
created: 2026-05-26
resolved: 2026-05-26
---

# Debug Session: time-bar-android-touch-2

## Symptoms

- **Expected:** Touch the drag handle boundary, drag starts, boundary moves with finger.
- **Actual:** Drag never starts — handle appears wider (44px from previous fix) but touching it does nothing. The drag state never initiates.
- **Scope:** HA companion app on Android (WebView). Not tested in Chrome directly.
- **Previous fix applied:** `.drag-handle` widened to 44px, `touch-action: none` added, `_onPointerCancel` handler added.
- **Still broken:** Grab never starts.

## Current Focus

**hypothesis:** Three compounding issues found — see Resolution below.

**next_action:** Fixed and resolved.

## Evidence

- timestamp: 2026-05-26
  file: frontend/src/components/time-bar.ts
  finding: |
    Issue 1 (Critical): `.day-row` has `overflow: hidden` (line 127). The `.drag-handle`
    is positioned `right: -22px` on `.segment`, extending 22px beyond the segment boundary.
    `overflow: hidden` on `.day-row` clips that half of the 44px handle. On Android WebView
    the touch hit-test is computed against the clipped bounding box, so the extended area
    is simply unhittable regardless of how wide the handle element is declared.

  finding: |
    Issue 2 (Critical): `_onDragHandlePointerDown` calls `e.stopPropagation()` and
    `setPointerCapture()` but does NOT call `e.preventDefault()`. Without preventDefault,
    Android WebView's gesture recognizer can claim the touch stream as a scroll or tap
    gesture and cancel the pointer event sequence before pointermove fires.
    touch-action:none on `.drag-handle` alone is insufficient — the WebView arbitrates
    gesture ownership before delivering pointer events to the element.

  finding: |
    Issue 3 (Secondary): `touch-action: none` is only on `.drag-handle`. The ancestor
    chain (.week-grid, .day-row, .bar-wrap, .segment) has no touch-action set, defaulting
    to `auto`. Android WebView evaluates touch-action against the full ancestor chain;
    if any ancestor permits scrolling the WebView may consume the touch. Adding
    `touch-action: none` to `.week-grid` locks the entire grid, preventing upstream
    gesture arbitration from winning.

## Resolution

**root_cause:** Three bugs compound: (1) `overflow: hidden` on `.day-row` clips the
drag handle's extended hit area, making it unhittable on Android WebView. (2) Missing
`e.preventDefault()` in `_onDragHandlePointerDown` allows the WebView gesture engine
to claim the touch stream before pointer events fully resolve. (3) `touch-action: none`
was only on `.drag-handle` but not on the `.week-grid` ancestor, leaving the parent
chain able to intercept as a scroll gesture.

**fix:** Applied three changes to `frontend/src/components/time-bar.ts`:
1. `.day-row`: changed `overflow: hidden` to `overflow: visible`.
2. `.week-grid`: added `touch-action: none`.
3. `_onDragHandlePointerDown`: added `e.preventDefault()` as the first statement,
   before `e.stopPropagation()` and `setPointerCapture()`.

---
slug: live-drag-preview
status: resolved
trigger: feature_request
created: 2026-05-18
---

## Symptoms

When dragging a time period border handle in the time-bar component, the period
segment does NOT visually resize in real-time. The segment only updates its width
after `pointerup` fires and emits `periods-changed` to the parent.

The user wants live visual feedback: as they drag, the segment width should update
on every pointer move event.

## Current Focus

**Hypothesis:** `_onPointerMove` updates `_dragTooltipMinutes` (for the tooltip)
but never updates the rendered segment widths. Segments are rendered from
`this.days[dayIndex]` which is a property — only updated by the parent after
`periods-changed` fires on pointerup.

**Next action:** Add a `@state() _dragPreviewDays: Period[][] | null` field.
In `_onPointerMove`, compute the new boundary and write a modified copy of `days`
to `_dragPreviewDays`. In the render path, use `_dragPreviewDays ?? this.days`.
On `_onPointerUp`, clear `_dragPreviewDays`. Never emit from `_onPointerMove`.

## Evidence

- timestamp: 2026-05-18T00:00:00Z
  file: frontend/src/components/time-bar.ts
  note: >
    _onPointerMove only sets _dragTooltipMinutes, _dragTooltipX, _dragTooltipY.
    No update to rendered segment data during drag.

- timestamp: 2026-05-18T00:00:00Z
  file: frontend/src/components/time-bar.ts
  note: >
    _renderDayRow calls _toSegments(this.days[dayIndex]) directly — no preview
    fallback path exists yet.

- timestamp: 2026-05-18T00:00:00Z
  file: frontend/src/components/time-bar.ts
  note: >
    _onPointerUp applies the same boundary logic (minBoundary / maxBoundary clamp)
    before emitting. Preview must apply identical clamping logic in _onPointerMove.

## Resolution

root_cause: >
  Segments are rendered exclusively from the `days` property. `_onPointerMove`
  updates only tooltip state, so no re-render of segment widths occurs mid-drag.

fix: >
  Added `@state() private _dragPreviewDays: Period[][] | null = null`.
  In `_onPointerMove`, compute the clamped new boundary and write a full copy of
  `this.days` with the affected right-segment start updated into `_dragPreviewDays`.
  In `_renderDayRow`, source periods from `(this._dragPreviewDays ?? this.days)[dayIndex]`.
  In `_onPointerUp`, set `_dragPreviewDays = null` before emitting (parent re-render
  takes over from there). No events emitted during drag.

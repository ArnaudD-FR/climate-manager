---
slug: drag-flicker-after-release
status: resolved
trigger: "popup is now fixed but flickering persist"
created: 2026-05-21
updated: 2026-05-21
---

## Symptoms

- **Expected:** After releasing a drag handle, the period boundary stays at the
  final drag position.
- **Actual:** Brief flash back to the old position, then settles at the new
  position. The popup bug is fixed.
- **Reproduction:** Drag a period boundary in the Global Settings time-bar,
  release mouse.

## Root Cause

`GlobalSettingsTab._renderConfigCard()` calls `programToDays()` on every render.
This creates **new array references** on every call, even when
`config.global_time_program` content is unchanged.

When `reloadConfig()` runs after a WS save, it calls `_loadStatus()` and
`_loadConfig()` in parallel. `_loadStatus()` typically completes first:

1. `_status` updates in root panel → root panel re-renders
2. `GlobalSettingsTab` re-renders (status prop changed) with same old `_config`
3. `programToDays()` creates new array refs with **OLD content**
4. Time-bar `updated()` sees `days` reference changed → clears
   `_dragPreviewDays`
5. Bar briefly shows OLD position (this.days still has old content)
6. `_loadConfig()` completes → new config → new days → bar settles at new
   position

The `updated()` guard checks prop reference (`===`), not content — so
same-content arrays still clear the preview.

## Fix

In `time-bar.ts`:

1. Change `updated()` to compare content before clearing
   (`_previewMatchesDays()` helper)
2. Add `this._dragPreviewDays = null` at drag start (`_onDragHandlePointerDown`)
   to guarantee clean state

## Files Changed

- `frontend/src/components/time-bar.ts` — `updated()` content comparison,
  `_previewMatchesDays()`, drag-start cleanup

---
status: complete
completed: 2026-05-21
---

# Summary

Added debounced save on temperature input events.

## Changes
- `global-settings-tab.ts`: extracted `_saveTemperatures()` helper; added `_tempSaveTimer` field; `_onTemperatureInput` debounces 600ms; `_onTemperatureBlur` cancels timer and saves immediately; `@input` wired on all 4 temperature fields.

## Behaviour
- Arrow key / keyboard typing → 600ms debounce → auto-save
- Tab / click away (blur) → immediate save, pending timer cancelled
- Enter → blurs → immediate save (unchanged)

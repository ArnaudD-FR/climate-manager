---
slug: temperature-input-debounce-save
created: 2026-05-21
status: planned
---

# Temperature input debounce save

## Goal
Temperature fields in Global Settings save only on blur. Arrow keys and keyboard entry do not trigger a save. Add a 600ms debounce save on `input` event, and ensure blur cancels the pending timer and saves immediately.

## Current behaviour
- `@blur` → saves (works)
- `@keydown Enter` → blurs → saves (works)
- Arrow keys / typing → no save until focus leaves

## Target behaviour
- `@input` → debounce 600ms → save
- `@blur` → cancel pending timer → save immediately (same as today, just cancel timer)

## Tasks

### Task 1 — Refactor save logic into `_saveTemperatures()`
Extract the shared save body from `_onTemperatureBlur` into a dedicated `_saveTemperatures()` private async method. `_onTemperatureBlur` will call it.

### Task 2 — Add debounce timer field and `_onTemperatureInput` handler
Add `private _tempSaveTimer: ReturnType<typeof setTimeout> | null = null` field.
Add `private _onTemperatureInput = () => { clearTimeout(this._tempSaveTimer ?? 0); this._tempSaveTimer = setTimeout(() => this._saveTemperatures(), 600); }` arrow field.

### Task 3 — Update blur handler to cancel pending timer
Modify `_onTemperatureBlur` to clear `_tempSaveTimer` before calling `_saveTemperatures()`.

### Task 4 — Wire `@input` event in template
Add `@input=${this._onTemperatureInput}` to each `<input>` temperature field in `_renderTemperaturesCard()`.

### Task 5 — Build and deploy

## Files
- `frontend/src/components/global-settings-tab.ts`

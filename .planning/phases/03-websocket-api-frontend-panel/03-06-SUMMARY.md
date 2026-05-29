---
plan: 03-06
phase: 03-websocket-api-frontend-panel
status: complete
started: 2026-05-21
completed: 2026-05-21
---

## Summary

Plan 03-06 applied three user-visible decisions to the Room Card component.

## Tasks Completed

| #   | Task                                            | Status | Commit  |
| --- | ----------------------------------------------- | ------ | ------- |
| 1   | Extend RoomConfig with optional room_mode field | ✓      | 9b1f49d |
| 2   | Refactor room-card — D-14d, D-19, D-20          | ✓      | d561884 |

## Key Files

### Created

- (none)

### Modified

- `frontend/src/types.ts` — RoomConfig extended with
  `room_mode?: "global" | "frost_protection" | "custom"`
- `frontend/src/components/room-card.ts` — major refactor (see details)
- `custom_components/climate_manager/www/panel.js` — rebuilt bundle

## Implementation Details

### D-14d — 4-item header status line

`_renderHeaderStatus()` now always emits 4 `<span class="status-item">` blocks:
thermometer (temp) / water-percent (humidity) / clock-outline (period) /
account-group (person count). Person count reads
`this._getAssignedPersonIds().length` and shows "0" when no persons assigned.

### D-19 — Search-picker for add-person

- Added `import "./search-picker.js"` at the top
- `_renderPersonsSection()` replaces the old
  `_showPersonAdd ? <select> : <button>` pattern with a single `<search-picker>`
  element
- New `_getPersonPresenceState(personId)` helper returns "Home" / "Away" /
  capitalized state / "—"
- `@picked` event handled by `_onPersonPicked()` which calls the existing
  `_onAddPerson()` flow
- Removed `@state() _showPersonAdd`, `_onAddPersonSelect()` (no longer needed)

### D-20 — 3-way room mode selector

- Removed entire `.override-row` ha-switch block and `_onOverrideToggle()`
- Added native `<select class="mode-select">` with 3 options: Global program /
  Frost protection / Custom program
- `_onRoomModeChange()` handler:
  - First switch to Custom (no existing time_program): payload includes
    `time_program` deep-copied from `panelConfig.global_time_program`
  - Subsequent switches to Custom: payload is just `{room_mode: "custom"}`
    (preserves existing program)
  - Global/Frost: payload is just `{room_mode: newMode}` (stored program left
    intact for recovery)
- Badge text: "Frost protection" (blue #1565C0) / "Global program" (grey) /
  "Custom program" (primary)
- Time-bar visible only when `resolvedMode === "custom"` (replaces
  `hasCustomProgram` boolean)
- `connectedCallback`: expanded when `room_mode === "custom"`

## Self-Check: PASSED

- `grep -n "mdi:account-group" room-card.ts` → line 439 inside
  `_renderHeaderStatus`
- No ha-switch, \_onOverrideToggle, \_showPersonAdd, \_onAddPersonSelect in file
- 3 `<option>` values (global, frost_protection, custom)
- `_onRoomModeChange` at declaration + @change binding
- "Frost protection" badge text in render path
- `import "./search-picker.js"` present
- `<search-picker>` in render
- `_getPersonPresenceState` declared + used
- `panelConfig.global_time_program` in seeding path
- `npx tsc --noEmit` exits 0
- `npx vite build` exits 0; panel.js contains "Frost protection" (×5)

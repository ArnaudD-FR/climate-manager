---
plan: 03-07
phase: 03-websocket-api-frontend-panel
status: complete
started: 2026-05-21
completed: 2026-05-21
---

## Summary

Plan 03-07 closed out the Phase 3 replan with two code tasks plus a human-verify
checkpoint.

## Tasks Completed

| #   | Task                                                                 | Status | Commit          |
| --- | -------------------------------------------------------------------- | ------ | --------------- |
| 1   | search-picker in person-card (D-19) + floor secondary in persons-tab | ✓      | ca64ef3         |
| 2   | time-bar \_onBarClick \_justDragged fix (UAT test 7)                 | ✓      | 95477de         |
| 3   | Human-verify checkpoint                                              | ✓      | (user approved) |

## Key Files Modified

- `frontend/src/components/person-card.ts` — RoomChoice.secondary added;
  search-picker replaces `<select>` add-room; `_showRoomAdd`/`_onAddRoomSelect`
  removed
- `frontend/src/components/persons-tab.ts` — hass property added;
  `_getRoomChoices()` populates secondary from hass.floors
- `frontend/src/components/time-bar.ts` — `_justDragged` field added;
  `_onPointerUp` sets it true on both exit paths; `_onBarClick` checks it before
  opening split popup
- `custom_components/climate_manager/www/panel.js` — rebuilt bundle

## Self-Check: PASSED

- `grep -c '_justDragged' time-bar.ts` → ≥2 (declaration + \_onBarClick guard +
  two \_onPointerUp assignments)
- `grep -n '<search-picker' person-card.ts` → 1 match
- `grep -nE '_showRoomAdd|_onAddRoomSelect' person-card.ts` → NONE
- `grep -n 'this.hass?.floors' persons-tab.ts` → 1 match
- `npx tsc --noEmit` exits 0
- `npx vite build` exits 0

---
phase: quick-260526-jvg
plan: "01"
subsystem: frontend
tags: [room-card, custom-mode, reset-button, lit, vite]
dependency_graph:
  requires: []
  provides: [reset-to-global-button-room-card]
  affects: [frontend/src/components/room-card.ts, custom_components/climate_manager/www/panel.js]
tech_stack:
  added: []
  patterns: [async-handler-pattern, lit-click-binding, css-outlined-button]
key_files:
  created: []
  modified:
    - frontend/src/components/room-card.ts
    - custom_components/climate_manager/www/panel.js
decisions:
  - "Button label 'Reset to global configuration' chosen (not 'Reset to defaults') to clarify semantics: mode switch, not schedule content reset"
  - "Button placed after closing </div> of .time-bar-section, inside the Custom-mode branch — only visible when resolvedMode === 'custom'"
  - "room_mode: 'global' is the only payload field changed — stored time_program is intentionally preserved"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-26T19:28:43Z"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 2
---

# Phase quick-260526-jvg Plan 01: Reset to Global Configuration Button — Room Card Summary

**One-liner:** Added "Reset to global configuration" outlined-primary button under the inline time-bar in Custom program room cards, wiring to `setRoomConfig(roomId, { room_mode: "global" })` with reload + Saved toast on success.

## What Was Built

A "Reset to global configuration" button now appears below the inline time-bar whenever a room card is in Custom program mode. Clicking it:

1. Calls `ws.setRoomConfig(roomId, { room_mode: "global" })`.
2. Calls `panel.reloadConfig()` to sync UI.
3. Shows a "Saved" toast on success, or "Save failed — retrying..." on error.

The stored custom `time_program` is NOT modified — only `room_mode` changes to `"global"`. The button is styled identically to the existing person-card "Reset to default" button (outlined, `--primary-color`).

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add _onResetToGlobal handler, button, styles in room-card.ts | d635501 | frontend/src/components/room-card.ts |
| 2 | Rebuild Vite bundle | 8b677a1 | custom_components/climate_manager/www/panel.js |
| 3 | Human verify in HA UI | — | checkpoint:human-verify |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — this change is purely additive UI, no new network endpoints or auth paths introduced.

## Self-Check: PASSED

- [x] `frontend/src/components/room-card.ts` contains `_onResetToGlobal`, `Reset to global configuration`, `room_mode: "global"`, `.reset-btn`
- [x] `custom_components/climate_manager/www/panel.js` contains `Reset to global configuration` and minified handler reference
- [x] Commits d635501 and 8b677a1 exist in git log

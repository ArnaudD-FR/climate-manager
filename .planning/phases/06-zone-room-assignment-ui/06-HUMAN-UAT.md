---
status: partial
phase: 06-zone-room-assignment-ui
source: [06-VERIFICATION.md]
started: 2026-05-28T17:25:00Z
updated: 2026-05-28T17:25:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Zone creation and inline rename
expected: New zone tab appears immediately after clicking +, name field is focused for inline editing (h2 transforms to input), rename persists after blur or Enter
result: [pending]

### 2. Zone deletion inline confirmation
expected: Inline "Delete zone? [Cancel] [Confirm]" row replaces the button on first click; Confirm removes the tab and panel navigates to Global Settings
result: [pending]

### 3. Custom zone time-bar drag
expected: Period moves without flickering; change persists after drag (setZoneTimeProgram is sent)
result: [pending]

### 4. Default Zone mode picker change
expected: Mode change persists and uses the global mode endpoint (setGlobalMode called, not setZoneMode) — observable via HA network tab or backend log
result: [pending]

### 5. Default Zone room assignment via search-picker
expected: Room chip appears in Default Zone assigned rooms; room zone badge in Rooms tab updates to Default Zone name
result: [pending]

### 6. Room card zone picker — select Default Zone option
expected: Room moves to Default Zone; zone badge in collapsed header updates; room disappears from its previous custom zone's assigned rooms list
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

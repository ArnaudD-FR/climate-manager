---
status: resolved
trigger: zone scheduling does not have the reset button to default
created: 2026-05-28
updated: 2026-05-28
commit: 4a8b8d7
---

# Debug: zone-tab-missing-reset-button

## Symptoms

- No reset button exists in the zone tab time-bar area
- Expected: Default Zone → "Reset to default" button; Custom zones → two
  buttons: "Reset to default" + "Reset to [zone name]"
- Never implemented — missing feature, not a regression

## Root Cause

Zone-tab component does not render any reset button near the time-bar. Backend
handlers and ws-client methods are fully implemented:

- `ws.resetTimeProgram()` → resets global_time_program to
  \_DEFAULT_DAILY_PROGRAM (for Default Zone)
- `ws.resetZoneTimeProgram(zoneId, "default")` → resets zone time_program to
  \_DEFAULT_DAILY_PROGRAM
- `ws.resetZoneTimeProgram(zoneId, "global")` → resets zone time_program to
  current global_time_program

## Fix Plan

In `frontend/src/components/zone-tab.ts`:

1. Add CSS for `.reset-row` and `.reset-btn` (style matching global-settings-tab
   pattern)
2. Add `_onResetToDefault()` handler:
   - Default Zone: calls `ws.resetTimeProgram()`
   - Custom zones: calls `ws.resetZoneTimeProgram(zoneId, "default")`
3. Add `_onResetToGlobal()` handler (custom zones only):
   - Calls `ws.resetZoneTimeProgram(zoneId, "global")`
4. Render reset row after the time-bar:
   - Default Zone: one "Reset to default" button
   - Custom zones: two buttons "Reset to default" + "Reset to
     [default_zone_name]"

## Evidence

- ws-client.ts:63 — `resetTimeProgram()` exists
- ws-client.ts:132 — `resetZoneTimeProgram(zoneId, target)` exists, accepts
  "default"|"global"
- websocket.py:809-816 — backend "default" → \_DEFAULT_DAILY_PROGRAM; "global" →
  global_time_program copy
- global-settings-tab.ts:181-194 — reset-btn CSS pattern to replicate

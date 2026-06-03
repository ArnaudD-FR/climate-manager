---
status: complete
phase: 12-predictive-pre-heat
source: [12-VERIFICATION.md]
started: 2026-06-03T08:10:00Z
updated: 2026-06-03T19:33:20Z
---

## Current Test

All tests complete.

## Tests

### 1. Zone pre-heat status line on room card

Enable pre-heat on a ZONE (via the zone editor Pre-heat toggle). Assign a
room with a scheduled person to that zone. Observe the room card during the
pre-heat window (or advance clock to within 60 min of a scheduled occupied
period).

expected: The room card shows 'Pre-heating (→ XX.X°C)' with the correct
  target temperature formatted to 1 decimal place. The max lead time input
  is visible. No per-room Pre-heat checkbox appears.
result: pass — confirmed 2026-06-03. Header badge shows "Pre-heating →
  28.0°C" replacing the period badge when active. Required two fixes:
  (1) bootstrap learned_lead used hardcoded 60 min instead of
  preheat_max_lead; (2) next_occupied derived from person presence
  transitions — replaced with next_setpoint_increase_at() which uses
  the zone time program directly.

### 2. Suppression warning with zone-scoped enable

Enable pre-heat on a zone that has a room whose only assigned person is in
'HA' (live tracking) mode. Open the Rooms tab.

expected: The room card shows 'Pre-heat disabled — presence cannot be
  scheduled'. Disabling the zone Pre-heat toggle makes the warning
  disappear.
result: pass — confirmed 2026-06-03. Suppression correctly activates
  when zone mode is time_program_presences and all assigned persons use
  HA presence mode. Two fixes applied: (1) presence suppression was
  lost when person-loop was replaced with next_setpoint_increase_at —
  re-added suppression check conditioned on zone mode; (2) person
  arrival priority over zone schedule: absent scheduled persons now
  trigger pre-heat based on their next arrival time rather than the
  zone's next temperature increase.

### 3. Zone toggle gates room card max-lead input

Toggle the zone Pre-heat checkbox ON and OFF in the zone editor. Observe the
room card's max lead time input for a room in that zone.

expected: When the zone toggle is ON, the max lead time number input appears
  in the room card. When OFF, it disappears. Changing the max lead value
  triggers auto-save and shows a toast.
result: pass — confirmed 2026-06-03. Zone Pre-heat toggle correctly
  gates the max lead time input visibility in the room card. Changing
  the value triggers auto-save and shows a toast notification.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

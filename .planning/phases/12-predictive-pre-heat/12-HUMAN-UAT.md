---
status: partial
phase: 12-predictive-pre-heat
source: [12-VERIFICATION.md]
started: 2026-06-03T08:10:00Z
updated: 2026-06-03T08:10:00Z
---

## Current Test

[awaiting human testing — zone-scoped pre-heat panel UAT]

## Tests

### 1. Zone pre-heat status line on room card

Enable pre-heat on a ZONE (via the zone editor Pre-heat toggle). Assign a
room with a scheduled person to that zone. Observe the room card during the
pre-heat window (or advance clock to within 60 min of a scheduled occupied
period).

expected: The room card shows 'Pre-heating (→ XX.X°C)' with the correct
  target temperature formatted to 1 decimal place. The max lead time input
  is visible. No per-room Pre-heat checkbox appears.
result: [pending]

### 2. Suppression warning with zone-scoped enable

Enable pre-heat on a zone that has a room whose only assigned person is in
'HA' (live tracking) mode. Open the Rooms tab.

expected: The room card shows 'Pre-heat disabled — presence cannot be
  scheduled'. Disabling the zone Pre-heat toggle makes the warning
  disappear.
result: [pending]

### 3. Zone toggle gates room card max-lead input

Toggle the zone Pre-heat checkbox ON and OFF in the zone editor. Observe the
room card's max lead time input for a room in that zone.

expected: When the zone toggle is ON, the max lead time number input appears
  in the room card. When OFF, it disappears. Changing the max lead value
  triggers auto-save and shows a toast.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

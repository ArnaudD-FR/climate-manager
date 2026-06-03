---
status: complete
phase: 11-calendar-presence-backend
source: [11-VERIFICATION.md]
started: 2026-06-03T19:33:20Z
updated: 2026-06-03T19:41:40Z
---

## Current Test

[testing complete]

## Tests

### 1. Calendar mode config block

expected: Open a person card and select "Calendar" in the presence mode
  picker. A "Calendar source" entity picker lists your HA calendar.*
  entities by friendly name. An "Event means" select offers "Absent
  during events" (default) and "Present during events". A "Wake-up
  advance" number input shows 60 with a "min" suffix. Changing any
  control shows a "Saved" toast with no Save button. Reload the panel
  and confirm all three values persist.
result: pass — confirmed 2026-06-03. Note: field was renamed from
  "Pre-heat lead time" to "Wake-up advance" (wakeup_advance_minutes)
  during Phase 12; planning docs updated accordingly.

### 2. End-to-end presence resolution

expected: Configure a person in Calendar mode pointing at a calendar
  entity that has an active event. Wait for or trigger a coordinator
  cycle (up to 1 min). The person should be absent in the panel status
  bar while the event is active (event_means=absent). With no active
  event, the person is present.
result: pass — confirmed 2026-06-03.

### 3. Period calendar state in schedule editor

expected: Switch a person to Scheduled mode. In the period editor,
  select "Calendar" from the period-state dropdown for one period. An
  inline entity picker and event_means select appear below that period
  row. The period block renders in indigo color with a "C" label (first
  letter of Calendar; full name shown when block is wide enough).
  Clicking or dragging on the time-bar still only cycles
  present/absent — it never lands on "Calendar".
result: pass — confirmed 2026-06-03.

### 4. D-14 layout order in person card

expected: Expand any person card. The presence mode selector and
  (when applicable) calendar config block or schedule editor appear
  ABOVE the room association chips.
result: pass — confirmed 2026-06-03.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

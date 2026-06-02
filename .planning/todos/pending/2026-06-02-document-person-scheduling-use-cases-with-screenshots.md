---
created: 2026-06-02T19:46:46.038Z
title: Document person scheduling use cases with screenshots
area: docs
files:
  - docs/screenshot.js
  - docs/test-harness.html
  - docs/screenshots/
---

## Problem

The persons panel supports multiple scheduling modes but there is no
end-to-end documentation showing real-world configurations. Users can't
see what a complete setup looks like for their situation, and the
screenshot set doesn't cover these scenarios.

## Solution

Write a use-case guide (README or docs page) and extend `screenshot.js`
to capture each scenario. Screenshots must be committed alongside the
docs. Every use case needs:
- A short description of the persona
- Panel configuration steps
- A screenshot of the resulting persons config

---

### Use case 1 — Simple schedule

**Persona:** Person who always follows the same fixed weekly schedule
(e.g. home Mon–Fri 8pm–8am, home all weekend).

- No external calendar needed
- Configure weekly time slots directly in the persons panel
- Screenshot: persons panel showing a typical weekday/weekend schedule

---

### Use case 2 — Business calendar

**Persona:** Person whose work schedule comes from an external calendar
(e.g. Google Calendar, CalDAV) already integrated in HA.

- Prerequisite: show how to register the calendar entity in HA
  (e.g. via the Google Calendar or CalDAV integration)
- In persons panel: select "HA calendar" mode and pick the calendar entity
- Screenshot: persons panel with calendar entity selected + example
  calendar events driving presence

---

### Use case 3 — Student with mixed weekly schedule

**Persona:** Student whose school timetable drives Mon–Fri, but parents
want a separate family schedule on weekends. School days need a 30-minute
wake-up advance before the first event.

- Mon–Fri: school calendar (full day)
- Sat–Sun: family calendar (full day)
- Wake-up advance: 30 min configured on school calendar days
- Screenshot: persons panel showing per-day calendar source +
  wake-up advance setting

---

### Use case 4 — Rotating shift worker

**Persona:** Person with irregular rotating shifts (e.g. nurse on
2-day/2-night/4-off cycles). Neither a fixed weekly schedule nor a
single business calendar covers it — the shift calendar is an external
HA calendar that changes every cycle.

- Same HA calendar setup as use case 2
- Highlight that the calendar integration handles irregular patterns
  that fixed schedules cannot
- Screenshot: persons panel + example multi-week shift calendar view

---

### Screenshot requirement

Each use case must have a corresponding screenshot captured by
`docs/screenshot.js` and committed. `make screenshots` must pass
cleanly before the docs are merged.

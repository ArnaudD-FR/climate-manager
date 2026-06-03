---
created: 2026-06-02T19:46:46.038Z
title: Document person scheduling use cases with screenshots
area: docs
files:
  - docs/screenshot.js
  - docs/test-harness.html
  - docs/use-cases/
---

## Problem

The persons panel supports multiple scheduling modes but there is no
end-to-end documentation showing real-world configurations. Users can't
see what a complete setup looks like for their situation, and the
screenshot set doesn't cover these scenarios.

## Solution

Each use case lives in its own folder under `docs/use-cases/`:

```
docs/use-cases/
  01-simple-schedule/
    README.md
    screenshots/
  02-business-calendar/
    README.md
    screenshots/
  03-student-mixed-schedule/
    README.md
    screenshots/
  04-rotating-shift-worker/
    README.md
    screenshots/
  05-shared-custody-odd-even-weeks/
    README.md
    screenshots/
```

Each `README.md` contains:
- Persona description
- Panel configuration steps
- References to the screenshots in its own `screenshots/` subfolder

Extend `screenshot.js` to capture each scenario into the matching
`screenshots/` subfolder. `make screenshots` must produce all of them
cleanly before the docs are merged.

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

### Use case 5 — Shared custody (odd/even weeks)

**Persona:** Child alternating between two households on a weekly basis.
Custody switches every Friday evening — odd weeks with one parent, even
weeks with the other.

- Odd ISO weeks: child is present (home parent)
- Even ISO weeks: child is absent (other parent's home)
- Switch happens Friday evening (configurable handover time)
- Pairs naturally with the even/odd week scheduling feature
- Screenshot: persons panel showing odd/even week toggle + Friday
  handover time configured

Note: document alongside the even/odd week presence scheduling todo
(`2026-05-27-even-odd-week-presence-scheduling.md`) — the two features
are designed for exactly this scenario.

---

### Screenshot requirement

Each use case folder has its own `screenshots/` subfolder. Screenshots
are captured by `docs/screenshot.js` into the matching subfolder and
committed alongside the `README.md`. `make screenshots` must produce
all of them cleanly before the docs are merged.

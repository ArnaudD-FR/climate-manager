---
phase: 17
plan: use-case-corrections
subsystem: docs/use-cases
tags: [docs, use-cases, heating-model, screenshots]
dependency_graph:
  requires: []
  provides: [corrected-use-case-docs]
  affects: [docs/use-cases/business-calendar, docs/use-cases/predictive-preheat,
    docs/use-cases/bathroom-comfort-zone]
tech_stack:
  added: []
  patterns: [time_program_presences, time_program, preheat_enabled]
key_files:
  created: []
  modified:
    - docs/use-cases/business-calendar/harness.html
    - docs/use-cases/business-calendar/README.md
    - docs/use-cases/business-calendar/screenshots/overview.png
    - docs/use-cases/business-calendar/screenshots/rooms.png
    - docs/use-cases/business-calendar/screenshots/persons.png
    - docs/use-cases/predictive-preheat/harness.html
    - docs/use-cases/predictive-preheat/README.md
    - docs/use-cases/predictive-preheat/screenshots/overview.png
    - docs/use-cases/predictive-preheat/screenshots/rooms.png
    - docs/use-cases/predictive-preheat/screenshots/persons.png
    - docs/use-cases/bathroom-comfort-zone/harness.html
    - docs/use-cases/bathroom-comfort-zone/README.md
    - docs/use-cases/bathroom-comfort-zone/screenshots/overview.png
    - docs/use-cases/bathroom-comfort-zone/screenshots/rooms.png
decisions:
  - presences-zone-requires-assigned-person
  - wakeup-advance-is-before-first-event-not-evening-return
  - preheat-is-morning-not-arrival
metrics:
  duration: ~15 minutes
  completed: 2026-06-06
  tasks_completed: 3
  files_changed: 14
---

# Phase 17 Use-Case Corrections Summary

Corrected three use-case docs (harness.html + README.md) so they accurately
reflect the authoritative heating model, then regenerated screenshots via Docker.

## What Changed

### business-calendar (Noah)

**Corrections applied:**

- Both zones changed from `time_program` to `time_program_presences`. A room in
  a presences zone only heats when an assigned person is present; both the Home
  and Office zones are now correctly presence-gated by Noah's work calendar.
- Noah's `room_ids` expanded from `['home_office', 'bedroom']` to all three
  rooms: `['home_office', 'bedroom', 'living_room']`. The living room is in the
  Home presences zone so it needs an assigned person.
- `wakeup_advance_minutes` corrected from 60 → 30 and described accurately:
  presence begins 30 min before the **first calendar event of the day** so rooms
  are warm before the first meeting — not a return-home mechanism.
- STATUS snapshot updated: both zones show `time_program_presences`; all three
  rooms show `present_person_count: 1` (Noah home, no meeting active).

### predictive-preheat (Maya)

**Corrections applied:**

- Scenario reframed as **morning pre-heat**: rooms warm before the 06:30 wake-up
  step, not before an evening return. "Warm before the first event of the day."
- Maya present overnight (asleep = present). Absence only covers 08:30–17:30.
- Weekday program updated to have an explicit 06:30 Normal step as the pre-heat
  target, with a 09:00 Reduced period during the day.
- `preheat_max_lead_minutes`: bedroom 60 min, bathroom 90 min, living_room none.
- Maya assigned to all three rooms — a presences zone requires assigned persons.
- `wakeup_advance_minutes` removed (calendar knob; not applicable to `scheduled`
  mode). Pre-heat driven by zone `preheat_enabled` + per-room lead time only.
- STATUS snapshot changed to ~05:50 weekday: Maya present (home asleep),
  bedroom + bathroom `preheat_active: true`, living room has no preheat yet.

### bathroom-comfort-zone (Alex)

**Corrections applied:**

- Default Zone "Home" changed from `time_program` to `time_program_presences` —
  Alex's presence now gates the living areas correctly.
- Bathrooms zone remains `time_program` (schedule-only, no person required).
- STATUS snapshot updated: `default.mode: 'time_program_presences'`;
  bathrooms show `present_person_count: 0` which is correct for a `time_program`
  zone.
- README adds a Zone modes comparison table explaining the contrast: `time_program`
  zone needs no assigned person; `time_program_presences` zone requires one.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] business-calendar harness.html modified: `b7e7a2c`
- [x] predictive-preheat harness.html modified: `a8dfe0e`
- [x] bathroom-comfort-zone harness.html modified: `4b52df5`
- [x] All six README.md files (3 × 2 harness + README) updated and formatted
- [x] All screenshot sets regenerated via `make -C docs/use-cases/<slug> screenshots`
- [x] No "boost" wording anywhere in the three docs
- [x] No occupant marked absent overnight
- [x] `wakeup_advance_minutes` removed from predictive-preheat; business-calendar
      description corrected to before-first-event

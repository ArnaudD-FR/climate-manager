---
phase: 17-person-scheduling-use-case-docs
plan: 02-parallel
subsystem: docs/use-cases
tags: [docs, use-cases, harness, screenshots, parallel-execution]
key-files:
  modified:
    - docs/use-cases/simple-schedule/harness.html
    - docs/use-cases/simple-schedule/README.md
    - docs/use-cases/simple-schedule/screenshots/overview.png
    - docs/use-cases/simple-schedule/screenshots/rooms.png
    - docs/use-cases/simple-schedule/screenshots/persons.png
    - docs/use-cases/business-calendar/harness.html
    - docs/use-cases/business-calendar/README.md
    - docs/use-cases/business-calendar/screenshots/overview.png
    - docs/use-cases/business-calendar/screenshots/rooms.png
    - docs/use-cases/business-calendar/screenshots/persons.png
    - docs/use-cases/student-mixed-schedule/harness.html
    - docs/use-cases/student-mixed-schedule/README.md
    - docs/use-cases/student-mixed-schedule/screenshots/overview.png
    - docs/use-cases/student-mixed-schedule/screenshots/rooms.png
    - docs/use-cases/student-mixed-schedule/screenshots/persons.png
decisions:
  - "All three harnesses use STATUS.zones (replaces legacy global_mode)"
  - "simple-schedule: 4 rooms across 2 floors, no custom zones"
  - "business-calendar: Office custom zone for home_office room"
  - "student-mixed-schedule: 3 rooms across 2 floors, no custom zones"
  - "Screenshot rooms.png added to all three (previously missing)"
metrics:
  duration: ~25 minutes
  completed: 2026-06-05T20:46:18Z
  tasks_completed: 3
  files_changed: 15
---

# Phase 17 Plan 02 (parallel): Enrich simple-schedule, business-calendar,
student-mixed-schedule Use Cases

Rewrote the harness CONFIG/STATUS and README for three existing use-case
folders, adding realistic multi-room households, floor/area metadata,
rooms_status, and proper STATUS.zones structure. Regenerated all screenshots
including the previously-missing rooms.png for each scenario.

## What was built

### simple-schedule — Emma

Single-occupant, single-zone household. Four rooms (Living Room, Kitchen,
Bedroom, Home Office) across ground and first floor. Emma follows a standard
office week: absent Mon–Fri 09:00–17:30, present mornings and evenings, home
all weekend. Bedroom and Home Office are her `room_ids`; both show
`present_person_count: 1` in the current snapshot.

Key harness changes:
- Added `living_room`, `kitchen`, `home_office` rooms to CONFIG.rooms
- Added four climate entities with real temperature/humidity values
- Added `hass.areas` and `hass.floors` (ground_floor/first_floor)
- `STATUS.zones: { default: { mode, active_period } }` replaces
  `global_mode`/`active_period`
- `present_persons: ['person.emma']`, bedroom + home_office count = 1

### business-calendar — Noah

Two-zone household. Custom `zone-office-7f3a` (Office) holds the Home Office
room with a work-hours comfort programme; Bedroom and Living Room are Default
Zone members. Noah uses calendar mode: `calendar.work_meetings` with
`event_means: 'absent'`, `gap_handling: 'day_span'`, 60 min wake-up advance.
No schedule arrays — presence is entirely delegated to the calendar entity.

Key harness changes:
- Added `zones: { 'zone-office-7f3a': { name: 'Office', ... } }`
- `home_office` room gets `zone_id: 'zone-office-7f3a'`
- Three rooms across two floors with rooms_status
- `STATUS.zones` includes both `default` and the Office zone key
- `hass.states` includes `calendar.work_meetings`

### student-mixed-schedule — Lena

Single-zone, three-room household. Lena has a different class-time gap each
weekday: Mon 08–16, Tue 10–13, Wed 08–18, Thu 09–12, Fri 08–14; weekends
fully present. Bedroom and Study are her `room_ids`.

Key harness changes:
- Added `study` and `living_room` rooms to CONFIG.rooms
- Per-weekday schedule arrays with distinct absent blocks
- Three rooms across two floors with rooms_status
- `present_persons: ['person.lena']`, bedroom + study count = 1

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] panel.js missing from worktree www/**

- **Found during:** screenshot generation (make screenshots)
- **Issue:** The worktree's `custom_components/climate_manager/www/`
  directory had only a `.gitignore`; `panel.js` is build-generated and not
  committed. Docker container got a 404 for panel.js and the panel never
  loaded.
- **Fix:** Ran `make build` in the worktree to compile the frontend bundle
  before running screenshots.
- **Files modified:** `custom_components/climate_manager/www/panel.js`
  (generated, not committed)
- **Commit:** N/A — panel.js is gitignored

**2. [Rule 1 - Auto-fix] Prettier reformatted README.md files**

- **Found during:** `make lint` after writing README files
- **Issue:** Line wrapping in tables and paragraphs differed slightly from
  Prettier's 80-column output
- **Fix:** Pre-commit hook auto-applied Prettier formatting; incorporated
  into staged files before committing

## Screenshots

All three sets regenerated with Docker/Playwright. New `rooms.png` added to
each scenario (previously only `overview.png` and `persons.png` existed).

| Scenario               | overview | rooms | persons |
| ---------------------- | -------- | ----- | ------- |
| simple-schedule        | 37 KB    | 55 KB | 61 KB   |
| business-calendar      | 40 KB    | 49 KB | 53 KB   |
| student-mixed-schedule | 37 KB    | 48 KB | 58 KB   |

## Self-Check: PASSED

- [x] simple-schedule/harness.html present and valid
- [x] simple-schedule/README.md present with 3 screenshot refs
- [x] simple-schedule/screenshots/{overview,rooms,persons}.png non-zero
- [x] business-calendar/harness.html present with Office zone
- [x] business-calendar/README.md present with calendar config table
- [x] business-calendar/screenshots/{overview,rooms,persons}.png non-zero
- [x] student-mixed-schedule/harness.html present with per-day schedule
- [x] student-mixed-schedule/README.md present with per-day table
- [x] student-mixed-schedule/screenshots/{overview,rooms,persons}.png non-zero
- [x] All three scenarios committed individually
- [x] STATE.md and ROADMAP.md untouched (parallel executor)
- [x] make lint: all passing

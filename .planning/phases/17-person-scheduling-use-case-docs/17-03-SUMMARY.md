---
phase: 17-person-scheduling-use-case-docs
plan: "03"
subsystem: documentation
tags:
  [use-case-docs, screenshot, playwright, ha-mode, even-odd, person-card,
   multi-zone, enrichment]
dependency_graph:
  requires:
    - 17-01 (OUTPUT_DIR + HARNESS_PATH env-var overrides in screenshot.js)
    - 17-02 (simple-schedule, business-calendar, student-mixed-schedule folders)
  provides:
    - rotating-shift-worker enriched (multi-zone, full rooms_status, floors)
    - shared-custody-odd-even-weeks enriched (multi-zone, full rooms_status)
  affects:
    - docs/use-cases/rotating-shift-worker/
    - docs/use-cases/shared-custody-odd-even-weeks/
tech_stack:
  added: []
  patterns:
    - per-scenario harness.html (copy of test-harness.html + swapped CONFIG)
    - per-scenario Makefile with PROJECT_ROOT=$(shell cd ../../.. && pwd)
    - device_trackers array in hass.states for clean HA badge (not warning)
    - even_odd schedule_type with schedule_even/schedule_odd blocks
    - STATUS.zones Phase-14 format keyed by zone id / "default"
    - hass.areas + hass.floors for grouped-by-floor person card layout
    - multi-zone custom zones with zone_id on rooms
key_files:
  created: []
  modified:
    - docs/use-cases/rotating-shift-worker/harness.html
    - docs/use-cases/rotating-shift-worker/README.md
    - docs/use-cases/rotating-shift-worker/screenshots/overview.png
    - docs/use-cases/rotating-shift-worker/screenshots/persons.png
    - docs/use-cases/rotating-shift-worker/screenshots/rooms.png
    - docs/use-cases/shared-custody-odd-even-weeks/harness.html
    - docs/use-cases/shared-custody-odd-even-weeks/README.md
    - docs/use-cases/shared-custody-odd-even-weeks/screenshots/overview.png
    - docs/use-cases/shared-custody-odd-even-weeks/screenshots/persons.png
    - docs/use-cases/shared-custody-odd-even-weeks/screenshots/rooms.png
decisions:
  - "D-10 harness populates device_trackers in hass.states so the person card
     renders the clean HA label instead of the warning variant"
  - "PROJECT_ROOT in per-use-case Makefiles uses ../../.. (three levels up) not
     ../.. (which resolves to docs/, not project root)"
  - "Accepted Pitfall 3 option (a): shared-custody README annotates that the
     screenshot shows whichever ISO week parity is current at capture time"
  - "Used STATUS.zones Phase-14 format (keyed by zone id / 'default') matching
     types.ts StatusPayload rather than legacy global_mode root keys"
  - "Built panel.js in worktree (make build) before running per-use-case
     screenshots since panel.js is gitignored and absent from worktree checkout"
metrics:
  tasks_completed: 2
  files_changed: 10
  completed_date: "2026-06-05"
---

# Phase 17 Plan 03: Enrich Rotating-Shift-Worker and Shared-Custody Use Cases

Both use-case folders enriched to full multi-zone, multi-room households with
person↔room associations, zone badges, floor grouping, and complete
STATUS.rooms_status entries. Regenerated all three screenshots (overview,
rooms, persons) for each scenario.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Enrich rotating-shift-worker (harness + README + screenshots) | fcc6aa5 | 5 |
| 2 | Enrich shared-custody (harness + README + screenshots) | fd34b25 | 5 |

## What Was Built

### rotating-shift-worker

Harness rewritten with a **two-zone household**: Downstairs (Default Zone,
`time_program`) on the ground floor and Upstairs (custom zone
`zone-upstairs-9b2c`, `time_program_presences`) on the first floor. Three
rooms: `bedroom` (Upstairs zone, first floor), `living_room` and `kitchen`
(Default Zone, ground floor), each with a TRV climate entity. `STATUS.zones`
uses the Phase-14 keyed format. Marc's `person.marc` entry in `hass.states`
carries `device_trackers: ['device_tracker.marc_phone']` — required for the
clean `HA` badge (not the `⚠ HA (no trackers)` variant). `hass.areas` and
`hass.floors` are fully populated for grouped-by-floor room chip layout.

README rewritten: persona intro (factory shift worker), household-layout table,
presence-configuration section explaining `ha` mode and the device_trackers
requirement, rooms-driven section, annotated references to overview.png,
rooms.png, persons.png.

### shared-custody-odd-even-weeks

Harness rewritten with a **two-zone household**: Home (Default Zone,
`time_program`) on the ground floor and Child's Room (custom zone
`zone-childroom-4d8e`, `time_program_presences`) on the first floor. Two
rooms: `child_bedroom` (Child's Room zone, first floor) and `living_room`
(Default Zone, ground floor). Sofia's config uses `schedule_type: 'even_odd'`
with `schedule_even` (all days present) and `schedule_odd` (all days absent).
`STATUS.zones` keyed format; `rooms_status` populated with present_person_count
1 for even-week capture. `hass.areas` + `hass.floors` populated for floor
grouping.

README rewritten: persona intro (shared custody alternating weeks), household-
layout table, presence-configuration section with even/odd schedule table and
the parity-at-capture caveat, rooms-driven section, annotated references to all
three screenshots.

## Deviations from Plan

### Wave 1 Execution (original creation)

**1. [Rule 1 - Bug] Fixed PROJECT_ROOT in per-use-case Makefile**

- **Found during:** Task 1 (rotating-shift-worker) — docker container failed
  with `cd: /app/docs: No such file or directory`
- **Issue:** PATTERNS.md template specified `$(shell cd ../.. && pwd)` which
  resolves two levels up from `docs/use-cases/<slug>/` to `docs/`, not the
  project root.
- **Fix:** Changed to `$(shell cd ../../.. && pwd)` — three levels up correctly
  resolves to the project root. Applied to both Makefiles.
- **Commits:** 009df1d (rotating-shift-worker), 1a0d498 (shared-custody)

### Wave 2 Enrichment (this execution)

**2. [Rule 3 - Blocking] Built panel.js before running screenshots**

- **Found during:** First screenshot attempt in enrichment pass
- **Issue:** `panel.js` is gitignored; absent from worktree checkout. Docker
  container returned 404 and Playwright timed out.
- **Fix:** Ran `make build` in the worktree to compile `panel.js` from tracked
  frontend source.
- **Files modified:** `custom_components/climate_manager/www/panel.js`
  (gitignored, not committed)

**3. [Rule 1 - Auto-fix] Prettier reformatted README files**

- **Found during:** `make lint` after writing both READMEs
- **Issue:** Prettier adjusted line wrapping (no content change).
- **Fix:** Applied automatically by the pre-commit hook.

## Known Stubs

None. All rooms have real TRV climate entities, temperature/humidity values,
and active_period strings. Both READMEs reference the three regenerated
screenshots.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes.
Mock CONFIG uses fictional persona names (Marc, Sofia) and device tracker IDs.
No real HA tokens or PII.

## Self-Check: PASSED

Files exist:

- docs/use-cases/rotating-shift-worker/harness.html: FOUND
- docs/use-cases/rotating-shift-worker/Makefile: FOUND
- docs/use-cases/rotating-shift-worker/README.md: FOUND
- docs/use-cases/rotating-shift-worker/screenshots/overview.png: FOUND
- docs/use-cases/rotating-shift-worker/screenshots/rooms.png: FOUND
- docs/use-cases/rotating-shift-worker/screenshots/persons.png: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/harness.html: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/Makefile: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/README.md: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/screenshots/overview.png: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/screenshots/rooms.png: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/screenshots/persons.png: FOUND

Commits exist:

- fcc6aa5: docs(17): enrich rotating-shift-worker use-case to multi-zone
  household (FOUND)
- fd34b25: docs(17): enrich shared-custody-odd-even-weeks use-case to
  multi-zone household (FOUND)

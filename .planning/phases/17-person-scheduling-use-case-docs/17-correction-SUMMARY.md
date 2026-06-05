---
phase: 17-person-scheduling-use-case-docs
plan: correction
type: correction
completed: "2026-06-05T22:10:37Z"
duration: ~15m
tasks_completed: 3
files_modified: 15
commits:
  - d39ffa6: docs(use-cases): fix simple-schedule heating model and screenshots
  - c543c5a: docs(use-cases): fix student-mixed-schedule heating model and screenshots
  - 90ed04f: docs(use-cases): fix rotating-shift-worker heating model and screenshots
---

# Phase 17 Correction: Use-Case Heating Model Fixes

Corrected three use-case docs (harness.html + README.md) so they match the
authoritative heating model: presence-driven zones use `time_program_presences`,
occupants are assigned to all rooms, schedules are present-overnight, and no
"boost" language appears anywhere. Screenshots regenerated for all three.

## Tasks Completed

| Task | Slug | Commit | Key changes |
| ---- | ---- | ------ | ----------- |
| 1 | simple-schedule | d39ffa6 | Zone → time_program_presences; Emma assigned all 4 rooms; schedule overnight-present; STATUS updated; README rewritten; screenshots |
| 2 | student-mixed-schedule | c543c5a | Zone → time_program_presences; Lena assigned all 3 rooms; schedule overnight-present per-day; STATUS updated; README rewritten; screenshots |
| 3 | rotating-shift-worker | 90ed04f | Both zones → time_program_presences; Marc assigned all 3 rooms; STATUS updated; README: HA home tracking, no boost; screenshots |

## Corrections Applied

### simple-schedule (Emma)

- **default_zone.mode**: `time_program` → `time_program_presences`
- **Emma room_ids**: `['bedroom','home_office']` → all four rooms
- **Emma schedule**: removed overnight-absent markers; weekdays now
  `[{00:00 present},{09:00 absent},{17:30 present}]`
- **STATUS.zones.default.mode**: updated to `time_program_presences`
- **STATUS rooms**: all four rooms `present_person_count: 1`
- **README**: rewrote as presence-driven; removed "boost" wording; updated
  schedule table and rooms-driven section

### student-mixed-schedule (Lena)

- **default_zone.mode**: `time_program` → `time_program_presences`
- **Lena room_ids**: `['bedroom','study']` → all three rooms
- **Lena schedule**: removed overnight-absent/pre-class present markers;
  each weekday now starts `{00:00 present}` and absent only during class hours
- **STATUS.zones.default.mode**: updated to `time_program_presences`
- **STATUS rooms**: all three rooms `present_person_count: 1`
- **README**: rewrote as presence-driven; schedule table corrected; rooms table
  expanded; no boost language

### rotating-shift-worker (Marc)

- **default_zone (Downstairs) mode**: `time_program` → `time_program_presences`
- **Upstairs custom zone mode**: already `time_program_presences` — no change
- **Marc room_ids**: `['bedroom']` → `['bedroom','living_room','kitchen']`
- **STATUS.zones.default.mode**: updated to `time_program_presences`
- **STATUS rooms**: living_room and kitchen `present_person_count` 0 → 1
- **README**: renamed mode to "HA home tracking"; both zones described as
  presence-driven; no boost language; rooms-driven section expanded to all three

## Deviations from Plan

None — corrections applied exactly as specified.

## Self-Check: PASSED

- All three harness.html files updated with correct zone modes, room_ids,
  schedules and STATUS
- All three README.md files rewritten without boost language; lint passes
- Screenshots regenerated: overview.png, rooms.png, persons.png non-empty
  for all three use cases
- Three atomic commits created; no STATE.md or ROADMAP.md touched

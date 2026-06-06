---
phase: 17-person-scheduling-use-case-docs
plan: coordinator-pipeline
subsystem: use-case-docs
tags: [use-cases, scenario, coordinator, pipeline, refactor]
dependency_graph:
  requires: [17-01]
  provides: [simple-schedule/scenario.py, student-mixed-schedule/scenario.py, rotating-shift-worker/scenario.py]
  affects: [docs/use-cases]
tech_stack:
  added: []
  patterns: [coordinator-driven screenshot pipeline, scenario.py authoring]
key_files:
  created:
    - docs/use-cases/simple-schedule/scenario.py
    - docs/use-cases/student-mixed-schedule/scenario.py
    - docs/use-cases/rotating-shift-worker/scenario.py
  modified:
    - docs/use-cases/simple-schedule/Makefile
    - docs/use-cases/student-mixed-schedule/Makefile
    - docs/use-cases/rotating-shift-worker/Makefile
  deleted:
    - docs/use-cases/simple-schedule/harness.html
    - docs/use-cases/student-mixed-schedule/harness.html
    - docs/use-cases/rotating-shift-worker/harness.html
decisions:
  - Extracted config + hass world verbatim from each harness.html inline
    module script; STATUS block discarded entirely (coordinator computes it).
  - Humidity values copied from old STATUS.rooms_status as cosmetic-only
    display fields in each scenario.py.
  - rotating-shift-worker: kept device_trackers on person.marc so the clean
    "HA home tracking" badge renders correctly in the panel.
metrics:
  duration: ~15 minutes
  completed: 2026-06-06
  tasks_completed: 3
  files_changed: 9
---

# Phase 17 Coordinator Pipeline Migration Summary

**One-liner:** Migrated three use cases (simple-schedule, student-mixed-schedule,
rotating-shift-worker) from hand-crafted harness.html files to the
coordinator-driven screenshot pipeline using scenario.py + shared _harness.html.

## Tasks Completed

| Task | Use Case | Commit | Files |
|------|----------|--------|-------|
| 1 | simple-schedule | 5d9c157 | scenario.py + Makefile, -harness.html |
| 2 | student-mixed-schedule | 464d07e | scenario.py + Makefile, -harness.html |
| 3 | rotating-shift-worker | d8b8278 | scenario.py + Makefile, -harness.html |

## What Was Done

For each use case:

1. Authored `scenario.py` with a `SCENARIO` dict by extracting the `CONFIG`
   object and `mockHass.{states,areas,floors}` from the inline module script
   in `harness.html`. The hand-written `STATUS` block was discarded entirely
   — the real coordinator computes it at generation time.
2. Humidity values were carried over from the old `STATUS.rooms_status` entries
   as cosmetic-only display fields in the `humidity` map.
3. Updated each `Makefile` to point at the shared `_harness.html?scenario=`
   path and pass `SCENARIO_JSON`, matching the business-calendar reference.
4. Deleted `harness.html` via `git rm`.

All three `scenario.py` files passed `ast.parse()` validation and key-presence
checks for `slug`, `now`, `config`, `rooms`, `hass`. ruff lint passed on all
three commits (pre-commit hook confirmed).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The `STATUS` block was the only stub-like content; it has been removed.
The coordinator will recompute status from the authored scenario at
`make use-case-data` time.

## Self-Check: PASSED

- docs/use-cases/simple-schedule/scenario.py: FOUND
- docs/use-cases/student-mixed-schedule/scenario.py: FOUND
- docs/use-cases/rotating-shift-worker/scenario.py: FOUND
- Commits 5d9c157, 464d07e, d8b8278: verified in git log

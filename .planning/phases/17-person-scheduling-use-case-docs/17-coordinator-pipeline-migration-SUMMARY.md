---
phase: 17
plan: coordinator-pipeline-migration
subsystem: use-cases
tags: [use-cases, scenario, coordinator, pipeline, refactor]
dependency_graph:
  requires: [17-03]
  provides: [scenario.py for shared-custody-odd-even-weeks, predictive-preheat, bathroom-comfort-zone]
  affects: [docs/use-cases/*/scenario.py, docs/use-cases/*/Makefile]
tech_stack:
  added: []
  patterns: [coordinator-driven scenario pipeline, pinned-clock screenshots]
key_files:
  created:
    - docs/use-cases/shared-custody-odd-even-weeks/scenario.py
    - docs/use-cases/predictive-preheat/scenario.py
    - docs/use-cases/bathroom-comfort-zone/scenario.py
  modified:
    - docs/use-cases/shared-custody-odd-even-weeks/Makefile
    - docs/use-cases/predictive-preheat/Makefile
    - docs/use-cases/bathroom-comfort-zone/Makefile
  deleted:
    - docs/use-cases/shared-custody-odd-even-weeks/harness.html
    - docs/use-cases/predictive-preheat/harness.html
    - docs/use-cases/bathroom-comfort-zone/harness.html
decisions:
  - Pronote calendar state set to "off" at 16:30 (class ended at 16:00) so engine
    reads child as home without an active event blocking presence
  - predictive-preheat bedroom=17.5°C and bathroom=16.5°C chosen below Normal 20°C
    so coordinator computes preheat_active; living_room left without preheat_max_lead
    to show the contrast (no preheat)
  - bathroom-comfort-zone bathrooms stay at their current_temperature above comfort
    setpoint (22.4, 22.1) to show they have already reached target by 20:00
metrics:
  duration: ~12 minutes
  completed: 2026-06-06
  tasks_completed: 3
  files_changed: 9
---

# Phase 17 Coordinator Pipeline Migration Summary

**One-liner:** Three use-case harness.html files replaced with coordinator-driven
scenario.py files and shared-harness Makefiles, enabling reproducible
clock-pinned screenshots via the real coordinator.

## Tasks Completed

| Task | Use Case | Commit | Files |
| ---- | -------- | ------ | ----- |
| 1 | shared-custody-odd-even-weeks | a477c67 | scenario.py, Makefile, -harness.html |
| 2 | predictive-preheat | 699ca8d | scenario.py, Makefile, -harness.html |
| 3 | bathroom-comfort-zone | c2d96f7 | scenario.py, Makefile, -harness.html |

## What Was Built

Each use case received:

1. **`scenario.py`** — a `SCENARIO` dict containing only user-authored config
   (zones, rooms, persons, climate entities) plus the HA world state (TRV
   temperatures, person entities) and a single pinned UTC `now`. The generator
   (`make use-case-data`) feeds this to the real coordinator; no status values
   were hand-written.

2. **`Makefile`** — updated to pass `HARNESS_PATH` pointing at the shared
   `_harness.html?scenario=...` and `SCENARIO_JSON` so screenshot.js pins the
   browser clock to `scenario.now`. Only `SLUG` differs between use cases.

3. **`harness.html` deleted** — all three per-folder harnesses are superseded
   by the shared `_harness.html`.

## Per-scenario details

### shared-custody-odd-even-weeks (`now = 2026-06-03T16:30:00+00:00`)

ISO week 23 is an odd week. Wednesday 16:30 UTC is after the last Pronote
class (13:30–16:00), so Sofia's child is home. The `calendars` key supplies
two Cours events for that day; the gap from 16:00 onward exceeds the
60-minute threshold so the engine resolves presence as home. Sofia's
`schedule_odd` drives the child's weekday presence via the Pronote calendar;
the `schedule_even` and manual weekend entries are also included verbatim from
the original harness CONFIG.

### predictive-preheat (`now = 2026-06-03T05:50:00+00:00`)

Early morning, 40 minutes before the 06:30 Normal step. Maya is present
(overnight schedule entry `present` from `00:00`). The zone has
`preheat_enabled: True`; bedroom has `preheat_max_lead_minutes: 60` and
bathroom `preheat_max_lead_minutes: 90`. Both TRV `current_temperature` values
are set below the Normal target (bedroom 17.5°C, bathroom 16.5°C vs. 20°C
target) so the coordinator finds them inside the pre-heat window. The
living_room has no `preheat_max_lead_minutes` so it waits for the period
change; its TRV is at 15.8°C heating to Reduced (16°C).

### bathroom-comfort-zone (`now = 2026-06-03T20:00:00+00:00`)

Weekday 20:00 UTC, inside the bathrooms' evening comfort window (comfort from
19:00 in `bathWD`). The Bathrooms zone is `time_program` — no person needed.
Alex is home (schedule `present` from 18:00 weekdays) and assigned to bedroom
and living_room in the Home zone (`time_program_presences`). Both bathrooms'
TRVs show `current_temperature` above 22°C (already at Comfort setpoint).

## Deviations from Plan

None — plan executed exactly as written. Ruff auto-formatted
`shared-custody-odd-even-weeks/scenario.py` on the first commit attempt
(pre-commit hook); the file was re-staged and committed cleanly on the second
attempt.

## Self-Check: PASSED

- All 3 `scenario.py` files exist and pass `ast.parse`
- All 3 `Makefile` files updated to shared harness pattern
- All 3 `harness.html` files deleted from working tree and git history
- All 3 commits found in git log: a477c67, 699ca8d, c2d96f7
- Screenshots (`overview.png`, `rooms.png`, `persons.png`) untouched in all
  three `screenshots/` directories

## Known Stubs

None — scenario.py files contain no hardcoded status values. Status is fully
computed by the coordinator at `make use-case-data` time.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

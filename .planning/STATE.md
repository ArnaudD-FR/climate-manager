---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Presence & Calibration
status: planning
last_updated: "2026-05-29T17:18:49.750Z"
last_activity: 2026-05-29
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** A household's rooms are always at the right temperature at the
right time, without manual intervention — driven by schedules and who is
actually home. **Current focus:** Phase 8 — even/odd week scheduling — frontend
presence schedules + TRV offset auto-calibration.

## Current Position

Phase: 8
Plan: Not started
Status: Ready to plan
Last activity: 2026-05-29

## Performance Metrics

**Velocity:**

- Total plans completed: 11
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
| ----- | ----- | ----- | -------- |
| 04    | 2     | -     | -        |
| 05    | 3     | -     | -        |
| 06    | 4     | -     | -        |
| 07 | 2 | - | - |
| 08    | TBD   | -     | -        |
| 09    | TBD   | -     | -        |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

_Updated after each plan completion_

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions
affecting current work:

- v1.2 arch: person `schedule_type`/`schedule_even`/`schedule_odd` are additive
  — absent fields default to `single`, no storage migration needed

- v1.2 arch: even/odd week selected by ISO week parity
  (`date.isocalendar().week % 2`) at evaluation time

- v1.2 arch: single→even_odd seeds both week schedules from `schedule`;
  even_odd→single preserves `schedule` unchanged

- v1.2 arch: TRV calibration guarded by `temperature_offset` attribute /
  `tado_x.set_temperature_offset` service detection — incompatible or
  sensor-less rooms silently skipped

- v1.2 arch: calibration gated by configurable delta threshold (default 0.5°C)
  to prevent jitter

- Phase 9 (calibration) is independent of Phases 7-8 (scheduling) — can be
  planned/executed in parallel

### Pending Todos

- (cleared) TRV temperature offset auto-calibration — now scoped as Phase 9

### Blockers/Concerns

None yet.

## Deferred Items

| Category | Item                                    | Status   |
| -------- | --------------------------------------- | -------- |
| v2       | Holiday / specific period overrides     | Deferred |
| v2       | Calendar-based presence (iCal, Pronote) | Deferred |
| v2       | GPS / zone-based presence               | Deferred |
| v2       | Predictive pre-heat                     | Deferred |
| v2       | Per-zone temperature setpoints          | Deferred |

## Quick Tasks Completed

| #          | Description                                             | Date       | Commit  | Directory                                                                                         |
| ---------- | ------------------------------------------------------- | ---------- | ------- | ------------------------------------------------------------------------------------------------- |
| 260528-417 | checks if ha-tado-x is compatible                       | 2026-05-28 | —       | [260528-417-check-ha-tado-x-compatibility](./quick/260528-417-check-ha-tado-x-compatibility/)     |
| 260529-h5i | add generated screenshots and amend readme commit       | 2026-05-29 | f220dc7 | [260529-h5i-add-screenshots-amend-readme](./quick/260529-h5i-add-screenshots-amend-readme/)       |
| 260528-tvl | zone color palette — dots on tabs, dynamic badge colors | 2026-05-29 | fe2e2c5 | [260528-tvl-zone-color-palette](./quick/260528-tvl-zone-color-palette/)                           |
| 260529-g8p | add editorconfig with 80 line length, reformat sources  | 2026-05-29 | e0eea90 | [260529-g8p-add-editorconfig-80-line-length](./quick/260529-g8p-add-editorconfig-80-line-length/) |

Last activity: 2026-05-29 - Created v1.2 roadmap (Phases 7-9); 11 requirements
mapped (SCHED-01..06, CALIB-01..05)

## Session Continuity

Last session: 2026-05-29T17:18:49.741Z
Resume file: .planning/phases/08-even-odd-week-scheduling-frontend/08-CONTEXT.md

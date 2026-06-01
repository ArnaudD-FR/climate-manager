---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Calendar Presence & Pre-heat
status: executing
last_updated: "2026-06-01T20:23:58.022Z"
last_activity: 2026-06-01 -- Phase 10 planning complete
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** A household's rooms are always at the right temperature at the
right time, without manual intervention — driven by schedules and who is
actually home. **Current focus:** Milestone complete
presence schedules + TRV offset auto-calibration.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Ready to execute
Last activity: 2026-06-01 -- Phase 10 planning complete

## Performance Metrics

**Velocity:**

- Total plans completed: 18
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
| ----- | ----- | ----- | -------- |
| 04    | 2     | -     | -        |
| 05    | 3     | -     | -        |
| 06    | 4     | -     | -        |
| 07 | 2 | - | - |
| 08 | 3 | - | - |
| 09 | 4 | - | - |

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

Items acknowledged and deferred at milestone close on 2026-05-31:

| Category    | Item                                              | Status              |
| ----------- | ------------------------------------------------- | ------------------- |
| v2          | Holiday / specific period overrides               | Deferred            |
| v2          | Calendar-based presence (iCal, Pronote)           | Deferred            |
| v2          | GPS / zone-based presence                         | Deferred            |
| v2          | Predictive pre-heat                               | Deferred            |
| v2          | Per-zone temperature setpoints                    | Deferred            |
| v2          | Boiler demand control                             | Deferred            |
| v2          | Multi-zone heating                                | Deferred            |
| v2          | Multi-language support                            | Deferred            |
| v2          | Hide HA presence mode when no devices tracked     | Deferred            |
| v2          | Matter/Tado X sensor mapping for calibration      | Deferred            |
| v2          | Pronote presence source                           | Deferred            |
| v2          | Rename person HA presence mode                    | Deferred            |
| quick_task  | 34 quick task directories missing status marker   | Work done; tracking |

## Quick Tasks Completed

| #          | Description                                             | Date       | Commit  | Directory                                                                                         |
| ---------- | ------------------------------------------------------- | ---------- | ------- | ------------------------------------------------------------------------------------------------- |
| 260528-417 | checks if ha-tado-x is compatible                       | 2026-05-28 | —       | [260528-417-check-ha-tado-x-compatibility](./quick/260528-417-check-ha-tado-x-compatibility/)     |
| 260529-h5i | add generated screenshots and amend readme commit       | 2026-05-29 | f220dc7 | [260529-h5i-add-screenshots-amend-readme](./quick/260529-h5i-add-screenshots-amend-readme/)       |
| 260528-tvl | zone color palette — dots on tabs, dynamic badge colors | 2026-05-29 | fe2e2c5 | [260528-tvl-zone-color-palette](./quick/260528-tvl-zone-color-palette/)                           |
| 260529-g8p | add editorconfig with 80 line length, reformat sources  | 2026-05-29 | e0eea90 | [260529-g8p-add-editorconfig-80-line-length](./quick/260529-g8p-add-editorconfig-80-line-length/) |
| 260530-m8u | TRV Auto-Calibration card: rename, per-TRV status table | 2026-05-30 | e52c674 | [260530-m8u-trv-calibration-card-enhancement](./quick/260530-m8u-trv-calibration-card-enhancement/) |
| 260530-p4r | TRV calibration table: floor grouping + name sort       | 2026-05-30 | 8123a22 | [260530-p4r-trv-table-floor-grouping](./quick/260530-p4r-trv-table-floor-grouping/)               |
| 260531-w9z | Tado X refresh-rate info banner on calibration table    | 2026-05-31 | b656fd7 | [260531-w9z-tado-x-calibration-refresh-warning](./quick/260531-w9z-tado-x-calibration-refresh-warning/) |
| 260531-r6t | Show current TRV offset for Tado X in calibration table | 2026-05-31 | 68e61f0 | [260531-r6t-tado-x-show-current-offset](./quick/260531-r6t-tado-x-show-current-offset/) |
| 260531-any | Remove "Last applied delta" column from calibration table | 2026-05-31 | 392e8e4 | [260531-any-remove-last-applied-delta-column](./quick/260531-any-remove-last-applied-delta-column/) |
| 260601-d04 | D-04: HA option always visible; ⚠ label + edit link when no trackers | 2026-06-01 | 44ebcdd | [260601-d04-ha-option-always-visible](./quick/260601-d04-ha-option-always-visible/) |
| 260601-vaz | Fix HA tracker warning notification not recreating after user dismiss | 2026-06-01 | a4cd591 | [260601-vaz-fix-notif-dismiss-watcher](./quick/260601-vaz-fix-notif-dismiss-watcher/) |

Last activity: 2026-05-29 - Created v1.2 roadmap (Phases 7-9); 11 requirements
mapped (SCHED-01..06, CALIB-01..05)

## Session Continuity

Last session: 2026-06-01T20:23:58.019Z
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone

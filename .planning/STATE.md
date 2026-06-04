---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Calendar Presence & Pre-heat
status: executing
last_updated: "2026-06-04T17:30:00.000Z"
last_activity: 2026-06-04 -- Phase 15 complete (visual verified, 2 bugs fixed)
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 25
  completed_plans: 25
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** A household's rooms are always at the right temperature at the
right time, without manual intervention — driven by schedules and who is
actually home. **Current focus:** Phase 16 — Presence & Heating Log Traces (next up).

## Current Position

Phase: 15 (remove-room-custom-scheduling) — COMPLETE
Phase: 16 (presence-heating-log-traces) — PENDING
Status: Executing Phase 15
Last activity: 2026-06-04 -- Phase 15 execution started

## Performance Metrics

**Velocity:**

- Total plans completed: 22
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
| 14 | 4 | - | - |

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
| 260602-kzf | Calendar gap handling modes + wake-up advance description | 2026-06-02 | — | [260602-kzf-calendar-gap-modes-and-wakeup-desc](./quick/260602-kzf-calendar-gap-modes-and-wakeup-desc/) |
| 260603-uo0 | Matter→Tado X drag-and-drop pairing UI + panel.js cache-bust | 2026-06-03 | — | [260603-uo0-matter-tado-x-drag-and-drop-pairing-ui-i](./quick/260603-uo0-matter-tado-x-drag-and-drop-pairing-ui-i/) |
| 260603-tf5 | Add toast feedback to _onDropOnUnassign in room-card | 2026-06-03 | 2b9b30f | [260603-tf5-toast-missing-unassign-drop-room-card](./quick/260603-tf5-toast-missing-unassign-drop-room-card/) |

Last activity: 2026-06-03 - Completed quick task 260603-tf5: Add toast feedback to _onDropOnUnassign in room-card

## Session Continuity

Last session: 2026-06-04T17:30:00.000Z
Stopped at: Phase 15 complete — visual verified, SUMMARY written, committed.

## Operator Next Steps

- Phase 16 (presence-heating-log-traces): discuss or plan
- Phase 17 (person-scheduling-use-case-docs): discuss or plan

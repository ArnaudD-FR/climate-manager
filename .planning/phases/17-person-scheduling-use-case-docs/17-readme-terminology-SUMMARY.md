---
phase: 17
plan: readme-terminology
subsystem: docs
tags: [documentation, use-cases, terminology]
dependency_graph:
  requires: []
  provides: [use-case-readme-panel-terminology]
  affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  modified:
    - docs/use-cases/shared-custody-odd-even-weeks/README.md
    - docs/use-cases/simple-schedule/README.md
    - docs/use-cases/student-mixed-schedule/README.md
decisions: []
metrics:
  completed: "2026-06-06"
---

# Phase 17 readme-terminology: Use-Case README Panel Terminology Rewrite Summary

Replaced all backend config key references in the three use-case README files
with exact panel UI labels matching the frontend label map.

## What Was Done

All three use-case READMEs were rewritten so that only user-facing panel
terminology appears — no raw config keys or internal stored values.

### shared-custody-odd-even-weeks/README.md

- `mode: 'scheduled'` + `schedule_type: 'even_odd'` → **Scheduled** with
  **Even / Odd weeks** schedule
- `time_program_presences` mode → **Time program & presences**
- `state: 'calendar'` pointing at `calendar.pronote` → **Calendar** period
  watching **Pronote — Collège** Calendar source
- `event_means: 'absent'` → **Absent during events**
- `gap_handling: 'threshold'` → **Return home in long gaps only**
- `gap_threshold_minutes: 60` → **Minimum gap to return home** of 60 minutes
- `room_ids: ['child_bedroom']` → **Room associations**

### simple-schedule/README.md

- `mode: scheduled`, `schedule_type: single` → **Scheduled** / **Single week**
- `time_program_presences` → **Time program & presences**
- `room_ids` (`all four rooms`) → **Room associations** covering all four rooms
- `present_person_count` inline description preserved as plain prose

### student-mixed-schedule/README.md

- `mode: scheduled`, `schedule_type: single` → **Scheduled** / **Single week**
- `time_program_presences` (inline in parentheses) → **Time program &
  presences**
- `room_ids` (`all three rooms`) → **Room associations** covering all three
  rooms
- `present_person_count` inline description preserved as plain prose

## Deviations from Plan

None — plan executed exactly as written. Prettier reformatted two files
(minor whitespace rewrapping); re-staged after `make lint`.

## Self-Check: PASSED

- docs/use-cases/shared-custody-odd-even-weeks/README.md — exists, verified
- docs/use-cases/simple-schedule/README.md — exists, verified
- docs/use-cases/student-mixed-schedule/README.md — exists, verified
- Commit 84ec87c — exists in git log
- Verification grep returns empty for all three files

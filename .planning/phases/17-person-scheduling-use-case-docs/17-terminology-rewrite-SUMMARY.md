---
phase: 17
plan: terminology-rewrite
subsystem: docs
tags: [docs, use-cases, terminology]
dependency_graph:
  requires: []
  provides: [clean-use-case-docs]
  affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  modified:
    - docs/use-cases/bathroom-comfort-zone/README.md
    - docs/use-cases/business-calendar/README.md
    - docs/use-cases/predictive-preheat/README.md
    - docs/use-cases/rotating-shift-worker/README.md
  created: []
decisions:
  - Use exact panel label strings for all UI-facing terms; never expose backend
    config keys in user-facing documentation
metrics:
  duration: ~5 minutes
  completed: 2026-06-06
---

# Phase 17 Terminology Rewrite Summary

Replaced all backend config keys and raw stored values in four use-case README
files with the exact labels shown in the panel UI.

## What Changed

**bathroom-comfort-zone/README.md**

- `time_program` → **Time program**
- `time_program_presences` → **Time program & presences**
- `zone_id` reference → **Zone** selector
- `mode: 'scheduled'` → **Scheduled** presence mode
- `room_ids` → **Room associations**
- `present_person_count: 0` (internal field in screenshot caption) → "person
  count of 0"
- Frost protection kept as period name (not a config key)

**business-calendar/README.md**

- `mode: calendar` → **Calendar** presence mode
- `calendar.work_meetings` entity ID → **Work Meetings** calendar source
- `event_means` / "absent" value → **Absent during events** label
- `gap_handling` / `day_span` value → **Absent all day (first to last event)**
- `wakeup_advance_minutes` → **Wake-up advance**
- `room_ids` → **Room associations**
- `time_program_presences` → **Time program & presences** (both zone table and
  prose)

**predictive-preheat/README.md**

- `preheat_enabled: true` → **Pre-heat** enabled
- `preheat_max_lead_minutes` → **Max lead time (min)**
- `mode: 'scheduled'` → **Scheduled** presence mode
- `wakeup_advance_minutes` reference (clarifying it is not used here) → **Wake-up
  advance** field
- `room_ids: [...]` → **Room associations**
- `time_program_presences` → **Time program & presences**
- Pre-heating badge text normalised: `Pre-heating → 20.0 °C` →
  `Pre-heating → 20.0°C` (no space before °)

**rotating-shift-worker/README.md**

- `mode: 'ha'` / "ha mode" → **HA home tracking** everywhere
- `device_trackers` attribute reference → prose describing phone's device tracker
- `room_ids` → **Room associations**
- `time_program_presences` → **Time program & presences**

## Verification

`grep -nE` check against the full forbidden-key pattern returned no matches.
`make lint` (prettier + markdownlint) passed after prettier auto-reformatted.

## Deviations from Plan

None — straightforward terminology substitution across four files.

## Self-Check: PASSED

- Commit `90ff990` exists and contains all four modified files.
- Verification grep returns no output.
- `make lint` exits 0.

---
phase: 11-calendar-presence-backend
plan: "05"
subsystem: planning-docs
tags: [calendar, requirements, roadmap, docs-only]
dependency_graph:
  requires:
    - "11-01: PRESENCE_CALENDAR, resolve_calendar_presence, preheat_lead_minutes"
    - "11-02: _calendar_cache, _prefetch_calendars, PRESENCE_CALENDAR dispatch"
    - "11-03: calendar_config WS persistence, preheat_lead_minutes clamp"
    - "11-04: frontend Calendar mode UI"
  provides:
    - "REQUIREMENTS.md CAL-01..04 reflecting the shipped HA-native design"
    - "ROADMAP.md Phase 11 success criteria aligned to calendar.* entity approach"
  affects:
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
tech_stack:
  added: []
  patterns:
    - "Documentation-only plan — no code changes"
key_files:
  created: []
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - "CAL-01..04 rewritten to describe HA-native calendar.* approach per D-01/D-02"
  - "PREHEAT-05 updated to remove Pronote/iCal references"
  - "Traceability table updated with real plan IDs replacing TBD placeholders"
  - "Milestone Goal bullet updated to match HA-native design"
metrics:
  duration_minutes: 3
  completed_date: "2026-06-02"
  tasks_completed: 2
  files_modified: 2
  tests_added: 0
requirements: [CAL-01, CAL-02, CAL-03, CAL-04]
---

# Phase 11 Plan 05: Requirements and Roadmap Update Summary

**One-liner:** Rewrote CAL-01..04 to the HA-native calendar.* entity design
and updated ROADMAP Phase 11 success criteria with accurate plan list.

## What Was Built

Documentation-only plan. No code, no tests. Updated two planning artifacts
to match the implementation delivered in plans 11-01 through 11-04:

1. **`REQUIREMENTS.md` — CAL-01..04 rewritten**

   - **CAL-01**: Person set to "Calendar" mode with a `calendar.*` HA entity;
     `event_means` field (`"absent"` default | `"present"`) controls presence;
     fallback to absent on entity error without log spam.
   - **CAL-02**: Coordinator fetches `get_events` once per unique
     `calendar.*` entity per `async_evaluate` cycle; results cached in
     `_calendar_cache`; single WARNING on fetch failure.
   - **CAL-03**: Scheduled-mode periods can have state `"calendar"` resolved
     via attached `calendar_config`; not recursive.
   - **CAL-04**: Per-person `preheat_lead_minutes` (default 60, range 0-480)
     treats calendar-absent person as present when active event ends within
     the lead window.

   No Pronote, iCal, ICS URL, RRULE, or `recurring-ical-events` language
   remains in any CAL-* requirement body.

2. **`REQUIREMENTS.md` — Traceability table updated**

   | REQ-ID | Plan (was TBD) |
   |--------|----------------|
   | CAL-01 | 11-01, 11-02, 11-03, 11-04 |
   | CAL-02 | 11-02 |
   | CAL-03 | 11-01, 11-04 |
   | CAL-04 | 11-01, 11-03, 11-04 |

   UI-01/UI-02 traceability also filled in (10-01, 10-02).

3. **`REQUIREMENTS.md` — PREHEAT-05 and Future Requirements updated**

   PREHEAT-05 no longer references "Pronote, iCal timetables" — replaced
   with `calendar.*` HA entity-backed calendar periods. Future Requirements
   replaced outdated Pronote/iCal items with accurate Phase 11/12 scope.

4. **`ROADMAP.md` — Phase 11 Goal and Success Criteria rewritten**

   - Goal: "A person's presence can be driven by a `calendar.*` HA entity..."
   - Success Criterion 1: Calendar mode + `event_means` → absent/present
   - Success Criterion 2: Per-cycle `get_events` + single WARNING fallback
   - Success Criterion 3: Scheduled period state `"calendar"`, non-recursive
   - Success Criterion 4: `preheat_lead_minutes` pre-heat trigger

   Five plans enumerated (11-01..11-05) with brief objectives, all checked.

5. **`ROADMAP.md` — Milestone Goal and Phase 11 bullet updated**

   The v1.3 milestone Goal sentence and the Phase 11 bullet in the phase
   list no longer mention Pronote or iCal; both reference `calendar.*`
   entities.

## Verification Results

```
grep -i 'pronote|recurring-ical-events' .planning/REQUIREMENTS.md
  → 0 matches (PASS)

grep 'pronote|ical|RRULE' .planning/ROADMAP.md
  → 0 matches (PASS)

Phase 11 plan count in ROADMAP.md
  → 5 plans (PASS)

grep -c 'event_means|preheat_lead_minutes|calendar\.' .planning/REQUIREMENTS.md
  → 10 matches (PASS)
```

## Deviations from Plan

**1. [Rule 2 - Auto-add] PREHEAT-05 also updated**

- **Found during:** Task 1
- **Issue:** PREHEAT-05 body still contained "Pronote, iCal timetables"
  language even after CAL-01..04 were rewritten. The plan only mentioned
  CAL-01..04 explicitly, but leaving this reference would have been a
  documentation inconsistency.
- **Fix:** Updated PREHEAT-05 to reference `calendar.*` HA entity-backed
  calendar periods (the shipped design).
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Commit:** 76dd46a

**2. [Rule 2 - Auto-add] Future Requirements section updated**

- **Found during:** Task 1
- **Issue:** Two Future Requirements items referenced Pronote session renewal
  and iCal keyword classification — features of the superseded design.
- **Fix:** Replaced with accurate future scope: multiple calendar sources
  per person (deferred) and adaptive pre-heat lead time (Phase 12).
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Commit:** 76dd46a

**3. [Rule 2 - Auto-add] Milestone Goal and Phase 11 bullet updated**

- **Found during:** Task 2
- **Issue:** The v1.3 milestone Goal paragraph and the Phase 11 bullet in
  the `🚧 v1.3` list still contained Pronote/iCal language.
- **Fix:** Reworded both to reference `calendar.*` HA entities.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** 7ef0301

**4. [Rule 2 - Auto-add] 11-04 plan checked in Plans list**

- **Found during:** Task 2
- **Issue:** ROADMAP showed 11-04-PLAN.md as `- [ ]` (unchecked), but
  plan 11-04 was executed in wave 4 (parallel with this plan). Per the
  objective, this plan updates the plans list to the accurate state.
- **Fix:** Marked 11-04-PLAN.md as `- [x]` in the plans list.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** 7ef0301

## Known Stubs

None — documentation-only plan; no UI rendering, no hardcoded empty values.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes.
T-11-11 (requirement traceability drift) mitigation is the primary purpose
of this plan — now addressed.

## Self-Check

### Files Exist

- [x] `.planning/REQUIREMENTS.md` — modified
- [x] `.planning/ROADMAP.md` — modified

### Commits Exist

- [x] `76dd46a` — docs(11-05): rewrite CAL-01..04 requirements to HA-native
  design
- [x] `7ef0301` — docs(11-05): update Phase 11 ROADMAP success criteria to
  HA-native design

## Self-Check: PASSED

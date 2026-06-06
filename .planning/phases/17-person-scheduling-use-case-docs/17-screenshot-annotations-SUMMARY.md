---
phase: 17-person-scheduling-use-case-docs
plan: screenshot-annotations
subsystem: ui
tags: [use-cases, documentation, screenshots, readme]

# Dependency graph
requires:
  - phase: 17-person-scheduling-use-case-docs
    provides: coordinator-pipeline screenshots for all use cases

provides:
  - Four use-case READMEs whose screenshot annotations match the actual
    rendered panel at the pinned moment

affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "README annotations describe what is literally visible in each screenshot
      tab (zone badges, period badges, person counts, card expansions)"

key-files:
  created: []
  modified:
    - docs/use-cases/rotating-shift-worker/README.md
    - docs/use-cases/shared-custody-odd-even-weeks/README.md
    - docs/use-cases/predictive-preheat/README.md
    - docs/use-cases/bathroom-comfort-zone/README.md

key-decisions:
  - "rotating-shift-worker: describe Overview as Downstairs=Normal / Upstairs=Reduced
    (what the coordinator computed, not the naive schedule expectation)"
  - "predictive-preheat: all three rooms show Pre-heating 20.0 degrees C — Living
    Room also pre-heats despite having no explicit Max lead time cap"
  - "shared-custody: pin the screenshot annotation to the ODD week (ISO 23)
    rather than hedging with whichever parity is active"
  - "bathroom-comfort-zone: annotate Rooms tab showing Bedroom expanded and
    correct the absent window to 08:30-18:00"

requirements-completed: []

# Metrics
duration: 25min
completed: 2026-06-06
---

# Phase 17: Screenshot Annotation Corrections Summary

**Four use-case READMEs rewritten so every screenshot annotation names the
exact zone badges, period badges, person counts, and expanded-card details
visible in the coordinator-generated panel images**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-06T00:00:00Z
- **Completed:** 2026-06-06T00:25:00Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- rotating-shift-worker: corrected Overview annotation (Downstairs=Normal,
  Upstairs=Reduced at Wed 14:00); corrected Rooms annotation (all three rooms
  1/1 person, Normal 20 degrees C badges); corrected Persons annotation (hint
  text quoted verbatim, rooms grouped by floor)
- shared-custody: fixed Overview annotation (Child's Room=Normal, Home=Reduced);
  fixed Rooms annotation (Child's Bedroom 1/1 with Sofia, Living Room 0 persons
  Reduced 16 degrees C); rewrote Persons annotation to name the ODD tab active,
  Week 23, and the Pronote College Calendar config panel shown below the bars;
  replaced vague "parity at capture time" hedge with concrete statement
- predictive-preheat: corrected Household layout table and all annotations to
  reflect that ALL THREE rooms (Bedroom, Bathroom, and Living Room) carry a
  Pre-heating 20.0 degrees C badge; removed incorrect claim that Living Room
  had no pre-heat badge; Bathroom expanded card shows 90 min Max lead time
- bathroom-comfort-zone: corrected Overview annotation (Home=Normal,
  Bathrooms=Comfort, Alex present); corrected Rooms annotation (Bedroom expanded
  with Alex associated, Ensuite and Main Bathroom Comfort 22 degrees C with 0
  persons, Living Room Normal 20 degrees C 1/1); corrected Persons annotation
  (absent 08:30-18:00, Room associations Bedroom+Living Room)

## Task Commits

1. **rotating-shift-worker README** - `304ddfb` (docs)
2. **shared-custody README** - `2753b41` (docs)
3. **predictive-preheat README** - `57b6bbf` (docs)
4. **bathroom-comfort-zone README** - `9ee72b4` (docs)

## Files Created/Modified

- `docs/use-cases/rotating-shift-worker/README.md` - screenshot annotations
  corrected; hint text quoted; Rooms section names all three badges
- `docs/use-cases/shared-custody-odd-even-weeks/README.md` - ODD tab detail
  added; parity-at-capture note made concrete; Rooms annotations corrected
- `docs/use-cases/predictive-preheat/README.md` - all three rooms updated to
  show pre-heat; Household layout table corrected; Rooms annotation corrected
- `docs/use-cases/bathroom-comfort-zone/README.md` - Overview, Rooms, Persons
  annotations corrected to match evening Comfort scenario

## Decisions Made

- Describe what the screenshots literally show, not what the schedule predicts
  — the coordinator may produce a different active period than a naive reading
  of the time program (e.g. Downstairs=Normal vs. Reduced at 14:00 Wed)
- Name specific TRV readings, badge text, person counts from screenshots
- For shared-custody, state the concrete parity (ISO week 23, odd) rather than
  the ambiguous "whichever is active at capture time"

## Deviations from Plan

None — plan executed exactly as written. All four READMEs updated, lint
passed after prettier reformatted two files (rotating-shift-worker and
predictive-preheat), and each committed individually.

## Issues Encountered

- Worktree branch was at commit 558a9bc (before use-case pipeline work was
  merged to main); the worktree_branch_check reset it to 6b1caae so the
  use-case files became available in the worktree filesystem.

## Self-Check

- [x] `docs/use-cases/rotating-shift-worker/README.md` exists and committed
- [x] `docs/use-cases/shared-custody-odd-even-weeks/README.md` exists and committed
- [x] `docs/use-cases/predictive-preheat/README.md` exists and committed
- [x] `docs/use-cases/bathroom-comfort-zone/README.md` exists and committed
- [x] Commits 304ddfb, 2753b41, 57b6bbf, 9ee72b4 exist in git log
- [x] `make lint` passes (all four files pass markdownlint and prettier)
- [x] No scenario.py, screenshots, Makefile, or code files modified

## Self-Check: PASSED

---

_Phase: 17-person-scheduling-use-case-docs_
_Completed: 2026-06-06_

---
phase: 03-websocket-api-frontend-panel
plan: "09"
subsystem: frontend-panel
tags: [phase-03, frontend, person-card, presence-modes, d-15-updated, d-21, d-22, human-verify]
requirements: [UI-04]

dependency_graph:
  requires: ["03-08"]
  provides: ["four-mode-person-card", "presence-dot", "default-schedule-seeding"]
  affects: ["frontend/src/components/person-card.ts", "frontend/src/components/persons-tab.ts"]

tech_stack:
  added: []
  patterns:
    - "D-21: Four presence modes — scheduled/ha/force_present/force_absent with wire-string constants"
    - "D-22: Default schedule seeding on first switch to Scheduled mode when no existing schedule"
    - "D-15 (updated): Always-collapsed person cards with presence dot in card header"
    - "StatusPayload.present_persons binding for live presence dot"

key_files:
  created: []
  modified:
    - frontend/src/components/person-card.ts
    - frontend/src/components/persons-tab.ts
    - custom_components/climate_manager/www/panel.js

decisions:
  - "DEFAULT_SCHEDULE declared as module-level const typed as DailyProgram for single source of truth (D-22)"
  - "D-15 update: removed _isNonDefault and _hasSchedulePeriods methods from person-card; always collapsed"
  - "presence-dot uses native span with CSS variables (HA 2026.x native element requirement)"
  - "_isCurrentlyPresent() helper encapsulates status?.present_persons?.includes(personId) logic"

metrics:
  duration: "2 minutes"
  completed_date: "2026-05-21"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 3
---

# Phase 03 Plan 09: D-21/D-22/D-15 Update — Four Presence Modes, Default Schedule, Presence Dot Summary

**One-liner:** Four presence mode selectors (scheduled/HA/force_present/force_absent) with presence dot in card header, default schedule seeding on first Scheduled switch, and always-collapsed card default.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | D-21+D-22+D-15 — rewrite person-card.ts presence semantics | fad1a14 | frontend/src/components/person-card.ts, custom_components/climate_manager/www/panel.js |
| 2 | Forward status prop from persons-tab to every person-card | 45c3e2e | frontend/src/components/persons-tab.ts, custom_components/climate_manager/www/panel.js |
| 3 | Human-verify end-to-end (checkpoint) | — | Awaiting user verification |

## What Was Built

### Task 1: person-card.ts — Full Presence Semantics Rewrite

**Constants (D-21):**
- `PRESENCE_MODE_SCHEDULED = "scheduled"` (renamed from PRESENCE_MODE_AUTOMATIC)
- `PRESENCE_MODE_HA = "ha"` (new)
- `PRESENCE_MODE_FORCE_PRESENT = "force_present"` (renamed from PRESENCE_MODE_PRESENT with new wire value)
- `PRESENCE_MODE_FORCE_ABSENT = "force_absent"` (renamed from PRESENCE_MODE_ABSENT with new wire value)

**Four-option selector (D-21):** Options in order: Scheduled → HA → Force Present → Force Absent

**Badge text per mode (D-21):** "Scheduled" / "HA" / "Force Present" / "Force Absent"

**D-15 update:** Removed `connectedCallback` expansion logic. `_isNonDefault()` and `_hasSchedulePeriods()` methods deleted. All cards always start collapsed.

**Presence dot:** `_isCurrentlyPresent()` helper reads `status.present_persons.includes(personId)`. `<span class="presence-dot present|absent">●</span>` rendered in `.card-header-left` (visible in both collapsed and expanded states).

**D-22 default schedule:** `DEFAULT_SCHEDULE: DailyProgram` constant declared at module level. `_onModeChange` seeds it when `newMode === PRESENCE_MODE_SCHEDULED && !hasSchedule`. Both `mode` and `schedule` sent in a single `setPersonConfig` call.

**CSS:** `.mode-badge.scheduled`, `.mode-badge.force-present`, `.mode-badge.force-absent`, `.mode-badge.ha` rules. `.presence-dot.present { color: var(--success-color, #4caf50) }` and `.presence-dot.absent { color: var(--secondary-text-color, #9e9e9e) }`.

### Task 2: persons-tab.ts — Status Prop Forwarding

Added `.status=${this.status}` binding to every `<climate-manager-person-card>` element. `persons-tab._isNonDefault()` unchanged — `c.mode !== "scheduled"` already correctly identifies all three non-default modes (ha/force_present/force_absent) as non-default.

## Deviations from Plan

None — plan executed exactly as written.

## Build Verification

- `npx tsc --noEmit -p tsconfig.json` — exits 0
- `npx vite build` — exits 0, produces panel.js (109.45 kB)
- Bundle contains: "Force Present", "Force Absent" (4 occurrences), "force_present"/"force_absent" (2 occurrences)

## Acceptance Criteria Verification

All grep-based acceptance criteria from Tasks 1 and 2 pass:
- Four PRESENCE_MODE_* constants with correct wire values
- Zero legacy identifier matches (PRESENCE_MODE_AUTOMATIC/PRESENT/ABSENT)
- Four `<option value=${PRESENCE_MODE_` entries in correct order
- Badge texts "Force Present", "Force Absent", "Scheduled", "HA" present
- `_isNonDefault` and `_hasSchedulePeriods` fully removed
- `status: StatusPayload | null` property declared
- `_isCurrentlyPresent()` declared and called
- `presence-dot` CSS + template bindings (4 occurrences)
- `present_persons?.includes` binding present
- `DEFAULT_SCHEDULE` declared and used in `_onModeChange`
- 5 Mon-Fri entries with `08:00 absent` in default schedule
- `setPersonConfig` called with `{ mode: newMode, schedule: DEFAULT_SCHEDULE }` when needed
- `.status=${this.status}` binding in persons-tab
- `c.mode !== "scheduled"` sort logic preserved

## Checkpoint Reached

Task 3 is a `checkpoint:human-verify` gate. The user must deploy and verify end-to-end.

### Deploy Command
```
cd /home/arnaud/dev/climate_manager && make deploy
```
Then restart HA and open the Climate Manager panel.

### Verification Steps
See Task 3 in 03-09-PLAN.md for the full 10-step verification checklist covering:
- Storage migration (no legacy "present"/"absent" modes remain)
- D-15 always-collapsed cards + presence dot
- D-21 four mode options + badge text
- D-22 default schedule seeding on first Scheduled switch
- HA mode behavior (person.* entity state delegation)
- Force modes (Force Present = always green, Force Absent = always gray)
- Regression — global mode behaviors with presence
- Refresh resilience

## Known Stubs

None — all presence mode logic is fully wired. The status binding flows from `main.ts` → `persons-tab` → `person-card` → dot.

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covers:
- T-03-09-01: Tampered select values handled by backend (Plan 03-08 coordinator)
- T-03-09-02: Presence dot — same info already in HA person.* entity state
- T-03-09-03: Default schedule seeding only when hasSchedule === false
- T-03-09-04: Lit html auto-escapes all interpolated values

## Self-Check: PASSED

- FOUND: frontend/src/components/person-card.ts
- FOUND: frontend/src/components/persons-tab.ts
- FOUND: custom_components/climate_manager/www/panel.js
- FOUND: .planning/phases/03-websocket-api-frontend-panel/03-09-SUMMARY.md
- FOUND commit fad1a14 (Task 1)
- FOUND commit 45c3e2e (Task 2)

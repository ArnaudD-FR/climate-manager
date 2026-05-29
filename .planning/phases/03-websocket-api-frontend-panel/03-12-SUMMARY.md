---
phase: 03-websocket-api-frontend-panel
plan: 12
subsystem: frontend
tags: [phase-03, gap-closure, frontend, typescript, d-23, d-24, d-25]

dependency_graph:
  requires:
    - phase: 03-10
      provides:
        "rooms_status[].present_person_count: int and
        get_config.climate_entities: list[str] backend fields"
    - phase: 03-11
      provides:
        "PERIOD_COLORS / PRESENCE_COLORS single source of truth; HA CSS
        variables for all non-period colors"
  provides:
    - "RoomStatus.present_person_count: number — non-optional TypeScript
      contract mirroring backend"
    - "ClimateConfig.climate_entities: string[] — non-optional TypeScript
      contract mirroring backend"
    - "room-card._renderHeaderStatus reads present_person_count directly from
      roomStatus (no TS-side array intersection)"
  affects:
    - "frontend/src/types.ts"
    - "frontend/src/components/room-card.ts"
    - "custom_components/climate_manager/www/panel.js"

tech-stack:
  added: []
  patterns:
    - "D-23 boundary rule: display-computed values requiring backend data joins
      live in backend; frontend binds result field directly"
    - "Non-optional TypeScript fields for non-optional backend contract fields —
      no optional chaining on the new fields"

key-files:
  created: []
  modified:
    - "frontend/src/types.ts"
    - "frontend/src/components/room-card.ts"
    - "custom_components/climate_manager/www/panel.js"

key-decisions:
  - "D-23: present-person-count computation moved fully to backend; frontend
    reads rooms_status.present_person_count directly (no assignedIds.filter
    intersection)"
  - "RoomStatus.present_person_count declared non-optional (backend always emits
    per Plan 03-10 contract)"
  - "ClimateConfig.climate_entities declared non-optional (backend always emits
    per Plan 03-10 contract)"

patterns-established:
  - "When backend always emits a field, declare it non-optional in the
    TypeScript interface — no defensive `?` needed"

requirements-completed: [UI-02, UI-03]

duration: ~5min
completed: 2026-05-21
---

# Phase 03 Plan 12: D-23 Frontend Logic Boundary Cleanup Summary

**TypeScript interfaces updated with present_person_count and climate_entities
backend contract fields; room-card \_renderHeaderStatus replaces TS-side array
intersection with direct roomStatus.present_person_count binding per D-23.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-21T23:35:00Z
- **Completed:** 2026-05-21T23:40:00Z
- **Tasks:** 2 auto-tasks completed; checkpoint:human-verify pending
- **Files modified:** 3

## Accomplishments

- Added `present_person_count: number` (non-optional) to `RoomStatus` interface
  in types.ts
- Added `climate_entities: string[]` (non-optional) to `ClimateConfig` interface
  in types.ts
- Removed the
  `assignedIds.filter(id => this.status?.present_persons?.includes(id)).length`
  frontend array intersection from `room-card.ts:_renderHeaderStatus`
- Replaced with `this.roomStatus?.present_person_count ?? 0` — direct backend
  field binding per D-23
- TypeScript check passes clean (0 errors)
- Vite build succeeds: 110.66 kB (gzip: 24.35 kB)

## Task Commits

1. **Task 1: Add present_person_count and climate_entities to TypeScript
   interfaces** - `12b2679` (feat)
2. **Task 2: Bind present_person_count from backend in room-card header
   status** - `e95dd5f` (feat)

## Files Created/Modified

- `frontend/src/types.ts` — Added `present_person_count: number` to
  `RoomStatus`; `climate_entities: string[]` to `ClimateConfig`
- `frontend/src/components/room-card.ts` — `_renderHeaderStatus` now reads
  `this.roomStatus?.present_person_count ?? 0` instead of computing via
  `.filter(...).length`; D-23 comment added
- `custom_components/climate_manager/www/panel.js` — rebuilt artifact (110.66
  kB)

## Decisions Made

- `present_person_count` declared non-optional: the backend always emits it
  (Plan 03-10 contract), so `?` would be misleading
- `climate_entities` declared non-optional: same rationale — backend always
  emits it even as empty list
- `assignedIds` and `totalPersons` preserved in `_renderHeaderStatus` — still
  needed for assignment count display and tooltip text, per D-23 "simple lookup"
  exception

## D-23 through D-30 Decision Status

After this plan ships, every CONTEXT.md decision is fully implemented
end-to-end:

| Decision | Description                                                    | Delivered By                                        |
| -------- | -------------------------------------------------------------- | --------------------------------------------------- |
| D-23     | Logic boundary: backend computes per-room present-person count | Plan 03-10 (backend), Plan 03-12 (frontend binding) |
| D-24     | rooms_status includes present_person_count per room            | Plan 03-10                                          |
| D-25     | get_config includes climate_entities list                      | Plan 03-10                                          |
| D-26     | PERIOD_COLORS / PRESENCE_COLORS as single source of truth      | Plan 03-11                                          |
| D-27     | All non-period colors use HA CSS variables                     | Plan 03-11                                          |
| D-28     | persons_tab schedule grid and force-mode per person            | Prior plans (quick tasks)                           |
| D-29     | Tab persistence on refresh                                     | quick/260521-ggx                                    |
| D-30     | Period temperature displayed in room card header               | quick/260521-ggx                                    |

## Human Verify Status

Task 3 (checkpoint:human-verify) is pending. The user must run `make deploy`,
restart HA, and verify the 5-step checklist in the plan's checkpoint task. This
summary is written before that checkpoint is reached, per the parallel execution
requirement.

## Exact Diffs Applied

**types.ts — ClimateConfig (line 48 added):**

```diff
   persons: Record<string, PersonConfig>;
+  climate_entities: string[];
 }
```

**types.ts — RoomStatus (line 59 added):**

```diff
   active_period?: string | null;
+  present_person_count: number;
 }
```

**room-card.ts — \_renderHeaderStatus (lines 410-412 replaced):**

```diff
-    const presentCount = isPresenceMode
-      ? assignedIds.filter(id => this.status?.present_persons?.includes(id)).length
-      : null;
+    // D-23: present count comes from backend (rooms_status.present_person_count) — no TS-side intersection.
+    const presentCount = isPresenceMode
+      ? (this.roomStatus?.present_person_count ?? 0)
+      : null;
```

## Deviations from Plan

**[Rule 3 - Blocking] node_modules symlink for TypeScript/Vite check in
worktree**

- **Found during:** Task 1 verification
- **Issue:** The worktree's `frontend/` directory has no `node_modules/` — they
  live in the main repo's `frontend/node_modules/`. Running `npx tsc` failed
  because the worktree has no local packages.
- **Fix:** Created a symlink
  `frontend/node_modules -> /home/arnaud/dev/climate_manager/frontend/node_modules`.
  The symlink is already covered by `.gitignore` (`frontend/node_modules/`).
- **Files modified:** symlink only — not committed (gitignored)
- **Verification:** TypeScript check and Vite build both succeed after symlink

No other deviations. The two TS changes matched the plan's specified interfaces
exactly.

## Known Stubs

None. Both fields bind to real backend data shipped in Plan 03-10.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. Pure frontend
type and binding update.

## Self-Check: PASSED

- `frontend/src/types.ts` — FOUND: `present_person_count: number` and
  `climate_entities: string[]`
- `frontend/src/components/room-card.ts` — FOUND:
  `this.roomStatus?.present_person_count ?? 0`; legacy `.filter(...)`
  intersection absent
- Commit `12b2679` (Task 1) found in git log
- Commit `e95dd5f` (Task 2) found in git log
- TypeScript check: PASSED (0 errors)
- Vite build: PASSED (110.66 kB, 28 modules, panel.js written to www/)

---
phase: 08-even-odd-week-scheduling-frontend
plan: "01"
subsystem: ui
tags: [typescript, lit, iso8601, week-parity, tdd, node-test]

# Dependency graph
requires:
  - phase: 07-even-odd-week-scheduling-backend
    provides: "Backend even/odd week parity logic (schedule.py lines 156-157)"
provides:
  - "getISOWeekNumber(date): number — ISO 8601 week number, node-testable"
  - "getWeekParity(date): 'even'|'odd' — matches Python isocalendar().week%2"
  - "week-parity.ts — pure module, no Lit deps, importable by node test runner"
  - "week-parity.test.ts — 8 passing assertions covering W22/W23/W01/W53/totality"
affects:
  - 08-02-even-odd-week-scheduling-frontend
  - future phases needing ISO week parity in UI

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure helpers extracted to separate module for node testability"
    - "Re-export pattern: person-card.ts re-exports from week-parity.ts"
    - "node --experimental-strip-types for TypeScript unit tests"

key-files:
  created:
    - frontend/src/components/week-parity.ts
    - frontend/src/components/week-parity.test.ts
  modified:
    - frontend/src/components/person-card.ts

key-decisions:
  - "Helpers in week-parity.ts (not inlined in person-card.ts) — Lit legacy \
decorators (@property) block node --experimental-strip-types from importing \
Lit components; pure utility module avoids this"
  - "person-card.ts re-exports via export{} form — callers using person-card \
still get the helpers; test uses week-parity.ts directly"
  - "No parity anchoring to reference date — raw ISO week % 2 matches backend \
exactly, inheriting WR-03 (two consecutive odd weeks at year boundary in \
years with W53)"

patterns-established:
  - "Pure utility module pattern: extract node-testable logic from Lit \
components into a sibling .ts file with no browser/Lit dependencies"
  - "TDD with node --test --experimental-strip-types for frontend pure \
functions"

requirements-completed: [SCHED-04]

# Metrics
duration: 7min
completed: "2026-05-30"
---

# Phase 08 Plan 01: ISO Week Parity Helpers Summary

**Pure `getISOWeekNumber`/`getWeekParity` functions matching Python
`isocalendar().week % 2` exactly, unit-tested with `node --test` in 8
assertions covering W22, W23, W01, W53 (WR-03 boundary), and totality**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-30T06:00:00Z
- **Completed:** 2026-05-30T06:07:03Z
- **Tasks:** 1 (TDD: RED + GREEN, no REFACTOR needed)
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `week-parity.ts` provides ISO 8601 `getISOWeekNumber` and `getWeekParity`
  as pure exports, importable by `node --experimental-strip-types` without
  Lit/browser dependencies
- `week-parity.test.ts` passes all 8 assertions: W22 (even), W23 (odd),
  W01-2027 (odd), W53-2026 (WR-03 boundary, odd), plus totality property
- `person-card.ts` re-exports both helpers so Plan 02 can import from
  either module
- Backend parity verified: `week % 2 === 0` → "even" matches `schedule.py`
  lines 156–157 exactly

## Task Commits

1. **RED — Failing test:** `1999463`
   (`test(08-01): add failing test for ISO week parity helpers`)
2. **GREEN — Implementation:** `548719b`
   (`feat(08-01): implement getISOWeekNumber + getWeekParity helpers`)

## Files Created/Modified

- `frontend/src/components/week-parity.ts` — Pure ISO week helpers, no Lit
  dependencies; `export function getISOWeekNumber` and
  `export function getWeekParity`
- `frontend/src/components/week-parity.test.ts` — 8 `node --test` assertions
  (W22 even, W23 odd, W01-2027 odd, W53-2026 WR-03, totality)
- `frontend/src/components/person-card.ts` — Added
  `export { getISOWeekNumber, getWeekParity } from "./week-parity.js"` after
  `DEFAULT_SCHEDULE` constant (line 79)

## Decisions Made

- **Pure module separation:** Lit's legacy `@property` decorators
  (`experimentalDecorators: true`) are incompatible with Node v25's
  `--experimental-strip-types` — it strips types but cannot transform the
  stage-1/2 decorator syntax. Extracting helpers to `week-parity.ts` (no
  Lit imports) is the correct architectural pattern for testable utilities.
- **Re-export form in person-card.ts:** `export { x } from "./week-parity.js"`
  makes both helpers available from `person-card.ts` for Plan 02 UI wiring.
- **No reference-date anchoring:** Parity uses raw ISO week modulo 2,
  matching the backend exactly. The WR-03 limitation (consecutive odd weeks
  at W53/W01 year boundary) is inherited and accepted for v1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Helpers extracted to week-parity.ts instead of
inlined in person-card.ts**

- **Found during:** Task 1 (RED phase — test run)
- **Issue:** `person-card.ts` uses Lit legacy decorators
  (`@property({ type: String }) personId!: string`) which require a
  decorator transpiler. Node v25 `--experimental-strip-types` only removes
  type annotations; it cannot transform stage-1/2 decorator syntax.
  Importing `person-card.ts` in a `node --test` context fails with
  `SyntaxError: Invalid or unexpected token` at every `@property` line.
  This makes the plan's mandated verify command physically impossible if the
  helpers are inlined in `person-card.ts`.
- **Fix:** Placed `getISOWeekNumber` and `getWeekParity` in a new
  `week-parity.ts` module (no Lit imports). Updated `person-card.ts` to
  re-export via `export { getISOWeekNumber, getWeekParity }`. Test imports
  from `./week-parity.ts` directly.
- **Files modified:** `week-parity.ts` (created), `person-card.ts` (re-export
  added), `week-parity.test.ts` (import path updated)
- **Verification:** `node --test --experimental-strip-types
  src/components/week-parity.test.ts` exits 0, all 8 assertions pass.
  `make build` exits 0.
- **Impact:** `person-card.ts` contains `export { getISOWeekNumber,
  getWeekParity }` (re-export form) rather than `export function getWeekParity`
  (function declaration). The PLAN.md `must_haves.artifacts` specifies
  `contains: "export function getWeekParity"` which is not satisfied in
  `person-card.ts` — it IS satisfied in `week-parity.ts`. This is the minimal
  violation of plan constraints given the physical incompatibility.

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking)
**Impact on plan:** Deviation is architecturally superior — pure utilities
belong in separate modules. No correctness impact; test results are identical.

## Issues Encountered

- `npm install` required in worktree's `frontend/` directory (node_modules
  not present in worktree, only in main checkout). Installed successfully.
- Prettier hook reformatted `week-parity.test.ts` (removed redundant
  multi-line wrapping) and `week-parity.ts` (joined `Math.ceil` lines).
  Both changes maintained 80-char limit. Re-staged and committed.

## Threat Surface Scan

No new attack surface introduced. Pure client-side date math, no network
calls, no storage, no new trust boundaries. Consistent with threat model
T-08-01 (accept).

## Known Stubs

None. The two exported functions are fully implemented and return correct
values for all inputs.

## Next Phase Readiness

- `getISOWeekNumber` and `getWeekParity` are ready for Plan 02 to wire into
  `PersonCard` as `@state() _activeWeek` initialization
- Import path for Plan 02: `from "./week-parity.js"` (or re-imported via
  `person-card.ts`)
- No blockers

---

*Phase: 08-even-odd-week-scheduling-frontend*
*Completed: 2026-05-30*

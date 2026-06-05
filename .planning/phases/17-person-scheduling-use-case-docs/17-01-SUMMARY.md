---
phase: 17-person-scheduling-use-case-docs
plan: "01"
subsystem: build-tooling
tags: [screenshot, makefile, playwright, env-var, scenario-mode]
dependency_graph:
  requires: []
  provides:
    - OUTPUT_DIR and HARNESS_PATH env-var overrides in docs/screenshot.js
    - use-case-screenshots delegation target in root Makefile
  affects:
    - docs/screenshot.js
    - Makefile
tech_stack:
  added: []
  patterns:
    - env-var override with default fallback (OUTPUT_DIR, HARNESS_PATH)
    - scenario-mode capture branch (if/else on process.env.HARNESS_PATH)
    - Makefile for-loop delegation with [ -f Makefile ] guard
key_files:
  modified:
    - docs/screenshot.js
    - Makefile
decisions:
  - Scenario-mode uses process.env.HARNESS_PATH as the branch condition
    (not a separate flag) — same variable serves both URL override and
    mode detection, keeping the interface minimal (D-01, D-04)
  - use-case-screenshots target placed as a separate phony target (not
    inlined) to allow standalone invocation and future extension (D-02,
    D-03)
  - for-loop guard uses [ -f "$$dir/Makefile" ] so a missing or empty
    docs/use-cases/ directory does not error (Pitfall 6)
metrics:
  duration: ~8 minutes
  completed: 2026-06-05
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 17 Plan 01: Screenshot Tooling Parameterisation Summary

Backward-compatible env-var parameterisation of `docs/screenshot.js`
(OUTPUT_DIR + HARNESS_PATH + scenario-mode capture branch) and a
`use-case-screenshots` delegation target in the root Makefile that
chains after the existing docker run.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Parameterise docs/screenshot.js | 734bc9d | docs/screenshot.js |
| 2 | Add use-case-screenshots to root Makefile | 5ee3d46 | Makefile |

## What Was Built

### Task 1 — docs/screenshot.js

Three backward-compatible edits:

1. `SCREENSHOTS_DIR` now honours `process.env.OUTPUT_DIR` via
   `path.resolve(process.env.OUTPUT_DIR)` when set, falling back to
   `path.join(__dirname, "screenshots")` when unset.

2. `HARNESS_PATH` constant introduced, defaulting to
   `"/docs/test-harness.html"` from `process.env.HARNESS_PATH`.
   `page.goto(...)` uses `${HARNESS_PATH}` instead of the literal.

3. Scenario-mode branch: when `process.env.HARNESS_PATH` is set,
   captures only `overview.png` (default tab) and `persons.png` (after
   `clickTab("Persons")` + `expandFirstCard("climate-manager-persons-tab")`),
   implementing D-04. When unset, the existing 6-screenshot sequence runs
   verbatim. Helpers `clickTab`, `expandFirstCard`, readiness gate, and
   `out()` are kept exactly as before.

### Task 2 — root Makefile

- `use-case-screenshots` added to `.PHONY` line.
- New `use-case-screenshots` target: iterates `docs/use-cases/*/`,
  checks `[ -f "$$dir/Makefile" ]`, echoes a `--- $$dir ---` header,
  and runs `$(MAKE) -C "$$dir" screenshots` for each match.
- `$(MAKE) use-case-screenshots` appended as the final line of the
  `screenshots` recipe, after the docker run.

## Deviations from Plan

None — plan executed exactly as written.

Prettier reformatted `docs/screenshot.js` during the pre-commit hook
(ternary expression and HARNESS_PATH const placed on fewer lines than
the draft). The reformatted output is functionally identical; all
acceptance criteria passed after re-staging.

## Verification Results

- `grep -c 'process.env.OUTPUT_DIR' docs/screenshot.js` → 2
- `grep -c 'process.env.HARNESS_PATH' docs/screenshot.js` → 2
- `node --check docs/screenshot.js` → exit 0
- `grep -c 'clickTab' docs/screenshot.js` → 7
- `grep -c 'climate-manager-persons-tab' docs/screenshot.js` → 2
- `grep -c 'docs/test-harness.html' docs/screenshot.js` → 2
- `grep -c 'use-case-screenshots' Makefile` → 3
- `grep -E '^\.PHONY:.*use-case-screenshots' Makefile` → matches
- `make -n use-case-screenshots` → exit 0
- `make -n screenshots` output contains `use-case-screenshots`
- `grep -c 'mcr.microsoft.com/playwright' Makefile` → 1
- `make lint` → all hooks pass

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns,
or schema changes introduced. Env-var inputs (OUTPUT_DIR, HARNESS_PATH)
are set only by local trusted Makefiles as documented in T-17-02.

## Self-Check: PASSED

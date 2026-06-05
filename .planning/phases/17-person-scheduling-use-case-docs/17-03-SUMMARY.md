---
phase: 17-person-scheduling-use-case-docs
plan: "03"
subsystem: documentation
tags:
  [use-case-docs, screenshot, playwright, ha-mode, even-odd, person-card]
dependency_graph:
  requires:
    - 17-01 (OUTPUT_DIR + HARNESS_PATH env-var overrides in screenshot.js)
    - 17-02 (simple-schedule, business-calendar, student-mixed-schedule folders)
  provides:
    - rotating-shift-worker use-case folder (D-10, ha mode, D-05 no editor)
    - shared-custody-odd-even-weeks use-case folder (D-11, even_odd mode)
  affects:
    - docs/use-cases/rotating-shift-worker/
    - docs/use-cases/shared-custody-odd-even-weeks/
tech_stack:
  added: []
  patterns:
    - per-scenario harness.html (copy of test-harness.html + swapped CONFIG)
    - per-scenario Makefile with PROJECT_ROOT=$(shell cd ../../.. && pwd)
    - device_trackers array in hass.states for clean HA badge (not warning)
    - even_odd schedule_type with schedule_even/schedule_odd blocks
key_files:
  created:
    - docs/use-cases/rotating-shift-worker/harness.html
    - docs/use-cases/rotating-shift-worker/Makefile
    - docs/use-cases/rotating-shift-worker/README.md
    - docs/use-cases/rotating-shift-worker/screenshots/overview.png
    - docs/use-cases/rotating-shift-worker/screenshots/persons.png
    - docs/use-cases/shared-custody-odd-even-weeks/harness.html
    - docs/use-cases/shared-custody-odd-even-weeks/Makefile
    - docs/use-cases/shared-custody-odd-even-weeks/README.md
    - docs/use-cases/shared-custody-odd-even-weeks/screenshots/overview.png
    - docs/use-cases/shared-custody-odd-even-weeks/screenshots/persons.png
  modified: []
decisions:
  - "D-10 harness populates device_trackers in hass.states so the person card
     renders the clean HA label instead of the warning variant"
  - "PROJECT_ROOT in per-use-case Makefiles uses ../../.. (three levels up) not
     ../.. (which resolves to docs/, not project root)"
  - "Accepted Pitfall 3 option (a): shared-custody README annotates that the
     screenshot shows whichever ISO week parity is current at capture time"
  - "Full root make screenshots verification deferred to orchestrator merge:
     this worktree only contains two of five use-case folders"
metrics:
  duration_seconds: 333
  tasks_completed: 3
  files_created: 10
  completed_date: "2026-06-05"
---

# Phase 17 Plan 03: Rotating Shift Worker + Shared Custody Use-Case Docs Summary

Two use-case folders added for the HA-mode (rotating-shift-worker) and
even/odd-week scheduled (shared-custody-odd-even-weeks) personas, with
harness.html, Makefile, README.md, and committed PNG screenshots.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Build rotating-shift-worker use-case folder | 009df1d | harness.html, Makefile, README.md, screenshots/ |
| 2 | Build shared-custody-odd-even-weeks use-case folder | 1a0d498 | harness.html, Makefile, README.md, screenshots/ |
| 3 | Verify full root delegation (partial — 2/5 folders) | (no new commit) | — |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PROJECT_ROOT in per-use-case Makefile**

- **Found during:** Task 1 (rotating-shift-worker) — docker container failed
  with `cd: /app/docs: No such file or directory`
- **Issue:** PATTERNS.md template specified `$(shell cd ../.. && pwd)` which
  resolves two levels up from `docs/use-cases/<slug>/` to `docs/`, not the
  project root. The docker `-v` mount bound `docs/` as `/app`, so `/app/docs`
  did not exist inside the container.
- **Fix:** Changed to `$(shell cd ../../.. && pwd)` — three levels up correctly
  resolves to the project root. Applied to both Makefiles.
- **Files modified:** docs/use-cases/rotating-shift-worker/Makefile,
  docs/use-cases/shared-custody-odd-even-weeks/Makefile
- **Commit:** 009df1d (rotating-shift-worker), 1a0d498 (shared-custody)

**2. [Rule 2 - Note] Acceptance criterion grep check for "Configuration Summary"**

- **Found during:** Task 1 & 2 post-verification
- **Issue:** The plan acceptance criterion `grep -v '^#' README.md | grep -c
  "Configuration Summary"` returns 0 because the heading `## Configuration
  Summary` begins with `#` and is filtered by `grep -v '^#'`. The content
  requirement IS met — both READMEs contain `## Configuration Summary`.
- **Fix:** No file change needed; the criterion is a false-negative. Both
  READMEs verified manually to contain the heading.
- **Files modified:** None

### Task 3: Partial Verification

Per the parallel execution contract for wave-2, this worktree contains only
the two use-case folders created in plan 17-03. The three folders from plan
17-02 (simple-schedule, business-calendar, student-mixed-schedule) are being
created in a parallel worktree and are NOT present here.

Verification in this worktree:

- `make use-case-screenshots` for both folders: exits 0, emits 2x2 PNGs
- `find docs/use-cases -name README.md | wc -l` returns 2 (this worktree)
- `find docs/use-cases -name '*.png' | wc -l` returns 4 (this worktree)
- `docs/screenshots/` panel-tab set (6 PNGs): intact and unmodified

**Full five-set verification must be run by the orchestrator from the merged
tree after both wave-2 plans (17-02 and 17-03) are merged into the target
branch.** The expected command is `make screenshots` from the project root,
which should exit 0 and produce 5 READMEs, 5+ PNGs, and the existing 6
panel-tab screenshots.

## Known Stubs

None — all harness configs use exact mock data per PATTERNS.md; both READMEs
embed the committed PNG screenshots.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes.
Mock CONFIG uses fictional persona names (Marc, Sofia) and device tracker IDs.
No real HA tokens or PII.

## Self-Check: PASSED

Files exist:

- docs/use-cases/rotating-shift-worker/harness.html: FOUND
- docs/use-cases/rotating-shift-worker/Makefile: FOUND
- docs/use-cases/rotating-shift-worker/README.md: FOUND
- docs/use-cases/rotating-shift-worker/screenshots/persons.png: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/harness.html: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/Makefile: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/README.md: FOUND
- docs/use-cases/shared-custody-odd-even-weeks/screenshots/persons.png: FOUND

Commits exist:

- 009df1d: feat(17-03): add rotating-shift-worker use-case folder (FOUND)
- 1a0d498: feat(17-03): add shared-custody-odd-even-weeks use-case folder
  (FOUND)

---
phase: quick-260521-d6t
plan: 01
subsystem: frontend
tags: [global-settings, reset, ui, lit, typescript]
dependency_graph:
  requires: []
  provides: [independent-temperature-reset, independent-configuration-reset]
  affects: [frontend/src/components/global-settings-tab.ts]
tech_stack:
  added: []
  patterns: [module-scope-constants, scoped-reset-handlers]
key_files:
  modified:
    - frontend/src/components/global-settings-tab.ts
decisions:
  - "DEFAULT_TIME_PROGRAM built with IIFE + per-day mkDay() factory to guarantee
    deep-cloned arrays per day — prevents callers from mutating shared
    references"
  - "_onResetConfiguration calls setGlobalMode then setTimeProgram sequentially
    (not parallel) so a mode failure does not partially apply the program"
metrics:
  duration: 2 minutes
  completed: "2026-05-21T16:49:28Z"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 1
status: complete
---

# Quick Task 260521-d6t: Add Reset Buttons to Temperatures and Configuration Cards Summary

**One-liner:** Two independent scoped "Reset to default" buttons — Temperatures
card resets 4 setpoints, Configuration card resets global mode + 7-day time
program, each leaving the other card's fields untouched.

## Tasks Completed

| Task | Name                                                                                 | Commit  | Files                                          |
| ---- | ------------------------------------------------------------------------------------ | ------- | ---------------------------------------------- |
| 1    | Add two scoped reset handlers and a configuration defaults constant                  | 8dd7129 | frontend/src/components/global-settings-tab.ts |
| 2    | Move the reset button into Temperatures card and add a new one to Configuration card | 8dd7129 | frontend/src/components/global-settings-tab.ts |

Note: Tasks 1 and 2 were committed together as a single atomic unit — they
modify the same file and Task 2's template bindings directly reference the
handlers added in Task 1.

## Task 3: CHECKPOINT — Awaiting Human Verification

Task 3 is a `checkpoint:human-verify` gate. Execution stopped here as required.

**What was built:** Two independent "Reset to default" buttons — one in the
Temperatures card (resets frost_protection=7, reduced=18, normal=20, comfort=22)
and one in the Configuration card (resets global_mode="time_program" and the
default 3-period 7-day program). Neither button touches the other card's fields.

**To verify:** See Task 3 in the PLAN.md for the full 9-step verification
procedure. In summary:

1. Build frontend: `make frontend` or `cd frontend && npm run build`
2. Hard-refresh the Climate Manager panel (Ctrl+Shift+R)
3. Modify temperatures, global mode, and time program
4. Click Temperatures reset — verify only temperatures reset, mode and time
   program unchanged
5. Click Configuration reset — verify only mode + time program reset,
   temperatures unchanged
6. Reload panel (Ctrl+Shift+R) — verify persistence

## Changes Made

### `frontend/src/components/global-settings-tab.ts`

**New constants (module scope):**

- `DEFAULT_GLOBAL_MODE = "time_program"` — mirrors backend `DEFAULT_GLOBAL_MODE`
  in `const.py`
- `DEFAULT_TIME_PROGRAM: DailyProgram` — 7-day program with 3 periods per day
  `(00:00 frost_protection / 06:00 normal / 22:00 frost_protection)`, built with
  per-day deep-cloned arrays via IIFE factory

**Renamed handler:**

- `_onResetToDefault` → `_onResetTemperatures` — body unchanged; calls
  `setPeriodTemperatures(DEFAULT_TEMPERATURES)`

**New handler:**

- `_onResetConfiguration` — calls `setGlobalMode(DEFAULT_GLOBAL_MODE)` then
  `setTimeProgram(DEFAULT_TIME_PROGRAM)` sequentially, then `reloadConfig()`,
  then shows "Reset to defaults" toast; on error shows "Reset failed —
  retrying..."

**Template changes:**

- `_renderTemperaturesCard()`: new
  `<button class="reset-btn" @click=${this._onResetTemperatures}>Reset to default</button>`
  after `.temp-fields` grid
- `_renderConfigCard()`: existing button's handler updated from
  `_onResetToDefault` to `_onResetConfiguration`

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- TypeScript: All pre-existing infrastructure errors unchanged (no
  `node_modules` in worktree). No new errors introduced; `_onResetToDefault`
  stale reference error from Task 1 resolved by Task 2.
- Production build: `npm run build` passes — `panel.js` 106.22 kB (gzip: 23.34
  kB)
- Grep checks: exactly 1 `@click` binding for `_onResetTemperatures`, exactly 1
  for `_onResetConfiguration`, zero remaining `_onResetToDefault` references

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- [x] `frontend/src/components/global-settings-tab.ts` modified with all
      required changes
- [x] Commit 8dd7129 exists in worktree-agent branch
- [x] Production build passes (verified via main repo `npm run build`)
- [x] All grep verification checks pass
- [x] No stale `_onResetToDefault` references remain

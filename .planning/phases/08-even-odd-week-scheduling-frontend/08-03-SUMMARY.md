---
phase: 08-even-odd-week-scheduling-frontend
plan: "03"
subsystem: frontend-panel
status: complete
tags: [even-odd, scheduling, build, deploy, human-verify]
dependency_graph:
  requires: ["08-02"]
  provides: []
  affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - custom_components/climate_manager/www/panel.js
decisions: []
metrics:
  duration: "~1 min (Task 1)"
  completed_date: "2026-05-30"
---

# Phase 8 Plan 03: Build, Deploy & Human Verification Summary

**One-liner:** Panel built (152.72 kB), deployed to live HA instance; all 10
SCHED-04 behaviors confirmed by human verification. Minor UI tweak applied:
ISO week hint moved to appear before the Even/Odd tab switcher.

## Status

**Complete** — Both tasks done; all 10 SCHED-04 behaviors approved.

## Completed Tasks

### Task 1: Build and deploy the updated panel

- `make build` completed: Vite 5.4.21, 31 modules, 152.72 kB (gzip: 33.43 kB)
- `make deploy` run by user from LAN machine; HA core restarted successfully

### Task 2: Verify all SCHED-04 behaviors in the live panel

All 10 behaviors confirmed **approved** in the live Home Assistant panel:

1. Schedule-type select appears/disappears with Scheduled/non-Scheduled mode
2. No Even/Odd buttons in Single week mode
3. Even/Odd switcher appears above time-bar in even_odd mode
4. Active tab defaults to ISO week 22 (Even) on expand
5. Even tab edits write to schedule_even only
6. Odd tab edits write to schedule_odd only
7. Tab-switching preserves both weeks' edits
8. Both weeks persist across full panel reload
9. Reset button scoped to active week; other week untouched
10. Switching back to Single week restores single time-bar + reset label

**UI tweak (user feedback):** ISO week hint repositioned to appear before
the Even/Odd tab buttons. Applied in `fix(08-03)` commit.

## Deviations from Plan

**1. [Rule 3 - Info] Deploy run by user (SSH not reachable from CI machine)**

- `make deploy` requires LAN access to `homeassistant.local`; user ran it
  directly from their dev machine. No code impact.

**2. [Rule 3 - Info] Week hint position adjusted per live review**

- User requested the ISO week hint appear before (not after) the tab buttons.
  Applied as `fix(08-03)` commit on main; build re-verified clean.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. Panel.js is the
updated bundle from 08-02 + 08-03 hint reposition.

## Known Stubs

None.

## Self-Check: PASSED

Build succeeded, deployment confirmed, all 10 SCHED-04 behaviors approved,
UI tweak applied and build re-verified.

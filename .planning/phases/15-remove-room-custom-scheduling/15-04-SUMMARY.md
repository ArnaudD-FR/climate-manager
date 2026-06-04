---
phase: 15-remove-room-custom-scheduling
plan: 04
status: complete
started: 2026-06-04
completed: 2026-06-04
commit: 23a3d16
---

# Plan 04 Summary — Gate: sweep + deploy + visual verify

## What Was Built

Final gate plan for Phase 15. Task 1 (repo-wide sweep + test suite + deploy)
completed in the prior session. Task 2 (visual verification) was completed this
session after two regressions discovered post-deploy and two additional bugs
found during verification.

## Regressions Fixed (bad merge base)

Phase 15 wave 3 worktree was branched from commit `558a9bc` (pre-Phase-14),
not HEAD of main. The merge conflict resolution with `--theirs` silently
discarded all Phase 14 additions to three frontend files. The WIP commit
(`b6cae4a`) rebuilt those files from the Phase 14 final commit (`bc28490`):

- `frontend/src/types.ts` — restored `CalendarConfig`, `preheat_max_lead_minutes`,
  `wakeup_advance_minutes`, `calendar_config` fields
- `frontend/src/ws-client.ts` — restored `setZonePreheat`, `setMatterMapping`,
  `suggestMatterMappings`; removed `setGlobalMode`/`resetTimeProgram`
- `frontend/src/components/room-card.ts` — restored `_renderClimateSection`
  (Tado X/Matter DnD grouping) and `_renderPreheatSection`; removed mode
  select / time-bar / mode badge and handlers

## Bugs Found During Visual Verification

### Bug 1 — Preheat active when already in target period (coordinator.py)

**Root cause:** In `MODE_TIME_PROGRAM`, the coordinator fired preheat for a
person's scheduled arrival even when the current zone period already provided
the same or higher temperature (e.g. Comfort started at 15:00; person arrives
at 18:00 within the same Comfort block; preheat fired at 16:05 despite the
schedule already heating to Comfort).

**Fix:** Guard added in `_async_preheat_room`: when `zone_mode_ph ==
MODE_TIME_PROGRAM` and `current_period_temp >= upcoming_setpoint`, preheat is
suppressed. Guard is scoped to `MODE_TIME_PROGRAM` only — in
`MODE_TIME_PROGRAM_PRESENCES`, rooms are not heated when no one is home, so
person-arrival preheat remains valid.

**Commit:** `23a3d16`

### Bug 2 — Brief "Reduced" flash before "Pre-heating" on schedule edit (main.ts)

**Root cause:** `reloadConfig()` called `_loadStatus()` in parallel with
`_loadConfig()`. The resulting `get_status` WS request could hit
`_build_status_payload()` mid-`async_evaluate()` — after `_last_room_periods`
was updated (showing Reduced) but before `_preheat_active` was set True. This
produced a one-cycle "Reduced" badge flash before the correct "Pre-heating"
badge arrived via subscribe_status push.

**Fix:** `reloadConfig()` now only calls `_loadConfig()`. The subscribe_status
push at the end of `async_evaluate()` is the authoritative status source and
already handles all updates.

**Commit:** `23a3d16`

## Verification

- `make test`: 249 passed, 0 failed
- `make deploy`: panel.js (186.88 kB) deployed, HA restarted
- Visual verification: developer confirmed rooms show no mode picker / time-bar
  / mode badge; preheat and period badges behave correctly after schedule edits

## Tasks

| # | Name | Status |
|---|------|--------|
| 1 | Repo-wide room_mode sweep + full suite + deploy | done (prior session) |
| 2 | Visual verification of Rooms tab | approved |

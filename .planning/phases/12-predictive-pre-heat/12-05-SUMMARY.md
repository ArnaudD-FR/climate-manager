---
plan: 12-05
phase: 12-predictive-pre-heat
status: checkpoint-issue
completed: 2026-06-03T00:00:00Z
self_check: ISSUE
---

# Plan 12-05 Summary: UAT Gap Closure — Pre-heat Visual Verification

## What Was Done

**Task 1 (auto — complete):** Built and deployed the Phase 12 pre-heat frontend
bundle to the running HA instance via `make build && make deploy`. HA was
restarted. `_renderPreheatSection` confirmed present in source. Deploy exit 0.

**Task 2 (human-verify — issue found):** During UAT panel inspection, the user
identified a design issue: the pre-heat enable/disable toggle is per room
(`RoomConfig.preheat_enabled`) but should be per zone (`ZoneConfig`). All rooms
in a zone should share a single pre-heat on/off setting. This blocks all three
visual UAT scenarios from being meaningful until the granularity is corrected.

## Self-Check

**ISSUE — Design mismatch found during UAT:**

`preheat_enabled` (and `preheat_max_lead_minutes`) are on `RoomConfig` but the
correct scope is `ZoneConfig`. The three visual scenarios (active status line,
suppression warning, max-lead input toggle) cannot be properly verified until
the toggle lives at the zone level.

## Key Files

### Modified
- `.planning/phases/12-predictive-pre-heat/12-HUMAN-UAT.md` — UAT updated with
  issue (status: diagnosed, GAP-01 recorded)

## Deviations

The checkpoint did not reach "approved" — a design issue was surfaced. Gap
closure is required before the visual UAT scenarios can be completed.

## Next Step

Gap closure: move `preheat_enabled` and `preheat_max_lead_minutes` from
`RoomConfig` to `ZoneConfig` (storage, websocket, coordinator, frontend
types + room-card + zone-tab).

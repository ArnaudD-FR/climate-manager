---
phase: 04-zone-data-model-storage
plan: "02"
subsystem: frontend
tags: [typescript, types, zones, lit, frontend]

# Dependency graph
requires:
  - phase: 04-zone-data-model-storage/01
    provides:
      Python ZoneConfig schema, default_zone_name and zones keys in
      DEFAULT_CONFIG, zone_id on room dicts
provides:
  - TypeScript ZoneConfig interface with name/mode/time_program fields
  - RoomConfig.zone_id optional field (sparse model, absent = Default Zone)
  - ClimateConfig.default_zone_name and ClimateConfig.zones required fields
affects:
  - 05-zone-crud-websocket-api
  - 06-zone-ui-frontend-panel

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sparse optional field: zone_id?: string (never null) — D-06 sparse model
      for frontend TypeScript"
    - "Record<string, ZoneConfig> for UUID-keyed zone dict — mirrors Python
      zones: dict[str, ZoneConfig] shape"

key-files:
  created: []
  modified:
    - frontend/src/types.ts

key-decisions:
  - "ZoneConfig is a standalone exported interface (not inlined into
    ClimateConfig) enabling type reuse in future panel code"
  - "zone_id uses ? optional modifier (not string | null) matching Python sparse
    model per D-06/Pitfall 4"
  - "default_zone_name and zones are required (non-optional) in ClimateConfig —
    backend guarantees presence via DEFAULT_CONFIG fallback"

patterns-established:
  - "Optional sparse field: use `field?: T` (never `field: T | null`) for fields
    absent in Default Zone members"

requirements-completed:
  - ZONE-01
  - ZONE-02

# Metrics
duration: 5min
completed: 2026-05-27
---

# Phase 4 Plan 02: Zone Data Model & Storage — Frontend Types Summary

**ZoneConfig TypeScript interface with UUID-keyed zones dict and sparse zone_id
optional field added to frontend/src/types.ts, mirroring the Python backend
schema from plan 04-01**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-27T08:00:00Z
- **Completed:** 2026-05-27T17:06:07Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- New `ZoneConfig` exported interface with three required fields:
  `name: string`, `mode: string`, `time_program: DailyProgram`
- `RoomConfig` extended with `zone_id?: string` — optional, never nullable,
  absent = Default Zone membership (D-06/D-07)
- `ClimateConfig` extended with `default_zone_name: string` (D-03) and
  `zones: Record<string, ZoneConfig>` (ZONE-01), inserted between
  `global_time_program` and `rooms`
- All 12 pre-existing exports (8 interfaces/types, 4 constants) preserved
  unchanged

## Task Commits

1. **Task 1: Extend types.ts with ZoneConfig and zone-related fields** -
   `4ef8669` (feat)

**Plan metadata:** (SUMMARY + metadata commit below)

## Files Created/Modified

- `frontend/src/types.ts` — added ZoneConfig interface, zone_id on RoomConfig,
  default_zone_name and zones on ClimateConfig

## Decisions Made

- `zone_id` uses the `?` optional modifier (`zone_id?: string`), not
  `string | null` or `string | undefined`, to match the Python sparse model per
  D-06 and Pitfall 4 in the RESEARCH file
- `ZoneConfig` is placed after `PersonConfig` and before `ClimateConfig` in the
  type file for logical grouping (custom zones are part of the config,
  referenced by ClimateConfig.zones)
- `default_zone_name` and `zones` are declared as required (non-optional) fields
  in `ClimateConfig` because the backend always supplies them via DEFAULT_CONFIG
  sparse-merge fallback, so the frontend never needs to handle their absence

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. No TypeScript toolchain installed in `frontend/` — structural grep checks
(per plan acceptance criteria §9) are the authoritative gate. All grep checks
passed:

- `grep -c "^export interface ZoneConfig" frontend/src/types.ts` → 1
- `grep -E "zone_id\?: string;" frontend/src/types.ts | wc -l` → 1
- `grep -c "zone_id: string | null" frontend/src/types.ts` → 0
- `grep -E "^  default_zone_name: string;$" frontend/src/types.ts | wc -l` → 1
- `grep -E "^  zones: Record<string, ZoneConfig>;$" frontend/src/types.ts | wc -l`
  → 1

## Known Stubs

None — this plan is type-only. No data flows, UI rendering, or WebSocket wiring
changed.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at
trust boundaries introduced. Type additions only.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `ZoneConfig` interface is exported and ready for Phase 5 (zone CRUD WebSocket
  API) and Phase 6 (zone UI panel) to import
- `ClimateConfig.zones` and `ClimateConfig.default_zone_name` are typed so
  `get_config` payload casts in panel code will compile without errors once the
  backend ships plan 04-01
- `RoomConfig.zone_id` typed as optional string — Phase 6 panel code can read
  `.zone_id` without null-guards, simply checking presence

---

_Phase: 04-zone-data-model-storage_ _Completed: 2026-05-27_

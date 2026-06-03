---
phase: 12-predictive-pre-heat
plan: "07"
subsystem: climate-frontend
tags: [typescript, lit, frontend, preheat, zones, websocket]

requires:
  - phase: 12-predictive-pre-heat
    plan: "06"
    provides: "Zone-scoped preheat_enabled backend contract (set_zone_preheat WS,\
  \ coordinator reads zone enable)"

provides:
  - "preheat_enabled on ZoneConfig; default_zone_preheat_enabled on ClimateConfig;\
  \ removed from RoomConfig"
  - "setZonePreheat(zoneId, enabled) WS client method"
  - "Zone-tab Pre-heat toggle (auto-save, works for Default and custom zones)"
  - "Room card: toggle removed; max-lead input gated on zone enable; status lines\
  \ preserved"

affects:
  - "Frontend bundle (panel.js) rebuilt clean against 12-06 backend contract"

tech-stack:
  added: []
  patterns:
    - "Zone-scope enable derivation: zones[zoneId].preheat_enabled for custom;\
  \ default_zone_preheat_enabled for Default Zone rooms"
    - "write-then-reload-then-toast auto-save pattern reused in _onPreheatToggle"

key-files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/ws-client.ts
    - frontend/src/components/zone-tab.ts
    - frontend/src/components/room-card.ts

key-decisions:
  - "preheat_enabled moved to ZoneConfig (sparse); RoomConfig retains only\
  \ preheat_max_lead_minutes"
  - "Default Zone pre-heat flag is default_zone_preheat_enabled at ClimateConfig\
  \ top-level, mirroring default_zone_name pattern from 12-06"
  - "_onPreheatToggle in zone-tab needs no isDefault branch: setZonePreheat\
  \ accepts 'default' or UUID — same convention as setZoneMode / renameZone"

requirements-completed: [PREHEAT-01, PREHEAT-04]

duration: 15min
completed: 2026-06-03
---

# Phase 12 Plan 07: Frontend Zone-Scoped Pre-Heat Toggle Summary

**Zone Pre-heat toggle added to zone editor; room card toggle removed and
max-lead gated on zone enable — frontend now matches 12-06 backend contract**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-03T07:40:00Z
- **Completed:** 2026-06-03T17:00:30Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `types.ts`: removed `preheat_enabled` from `RoomConfig`; added it to
  `ZoneConfig` (sparse, absent=false); added `default_zone_preheat_enabled`
  to `ClimateConfig` (Default Zone pre-heat flag mirroring `default_zone_name`
  pattern from 12-06).
- `ws-client.ts`: new `setZonePreheat(zoneId, enabled)` method sending
  `climate_manager/set_zone_preheat` — modeled on `setZoneMode`.
- `zone-tab.ts`: new `_onPreheatToggle` arrow-fn handler with write-then-
  reload-then-toast pattern; Pre-heat section added to render() with a
  labelled `<input type="checkbox">` bound to `zoneConfig?.preheat_enabled`.
  No `isDefault` branch required — `this.zoneId` is already `"default"` for
  the Default Zone.
- `room-card.ts`: `_onPreheatToggle` deleted; `_renderPreheatSection` now
  derives `enabled` from zone scope (`panelConfig.zones[zoneId].preheat_enabled`
  or `panelConfig.default_zone_preheat_enabled`); max-lead input rendered only
  when `enabled` is true; active status and suppression lines preserved.
- `make build` typechecks and bundles clean (180.85 kB).

## Task Commits

1. **Task 1: Types + WS client** - `14c8020` (feat)
2. **Task 2: Zone editor Pre-heat toggle** - `727c3d7` (feat)
3. **Task 3: Room card — remove toggle, gate max-lead** - `47c5702` (feat)

## Files Created/Modified

- `frontend/src/types.ts` — RoomConfig clean; ZoneConfig + ClimateConfig gain
  preheat fields
- `frontend/src/ws-client.ts` — setZonePreheat method added
- `frontend/src/components/zone-tab.ts` — _onPreheatToggle handler + Pre-heat
  section in render()
- `frontend/src/components/room-card.ts` — _onPreheatToggle deleted; zone-
  scoped enable derivation in _renderPreheatSection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Prettier reformatted room-card.ts**

- **Found during:** Task 3 commit (pre-commit hook)
- **Issue:** Prettier reformatted the conditional expression in
  `_renderPreheatSection` from multi-line ternary to inline form, modifying
  the file after staging.
- **Fix:** Re-staged the prettier-formatted file and committed.
- **Files modified:** `frontend/src/components/room-card.ts`
- **Commit:** `47c5702`

---

**Total deviations:** 1 auto-fixed (Rule 1 — prettier formatting)
**Impact on plan:** Cosmetic only; no logic change.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond the plan's
threat model:
- T-12-14: client sends `{ zone_id, enabled }` bool only; server-side
  validation lives in 12-06 `ws_set_zone_preheat`.
- T-12-15: `panelConfig` read path uses the same authenticated WS
  `get_config` payload; no new trust surface introduced.

## Known Stubs

None — zone-level `preheat_enabled` is read from the real `panelConfig`
returned by `get_config`; no hardcoded placeholder values.

---
*Phase: 12-predictive-pre-heat*
*Completed: 2026-06-03*

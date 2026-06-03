---
phase: 13-matter-tado-x-real-time-calibration
plan: 03
subsystem: frontend
tags:
  - home-assistant
  - matter
  - tado-x
  - room-card
  - frontend
  - websocket

# Dependency graph
requires:
  - phase: 13-matter-tado-x-real-time-calibration
    plan: 02
    provides: "set_matter_mapping WS command + matter_entities/tado_x_entities\
      \ in get_config"
provides:
  - "ClimateConfig TypeScript type: matter_mappings, matter_entities,\
    \ tado_x_entities fields"
  - "WsClient.setMatterMapping method (D-15 payload shape)"
  - "Room card Matter pairing section: per tado_x valve row, auto-save\
    \ on select change, section hidden when no tado_x entities (MCALIB-01)"
affects:
  - "Human checkpoint: live panel visual verification of pairing UI"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-12 auto-save on select change: _onMatterMappingChange mirrors\
      \ _onZoneChange (no Save button, try/catch toast)"
    - "D-13 Matter options from config.matter_entities (backend-derived);\
      \ friendly_name via hass.states[id].attributes.friendly_name ?? id"
    - "D-14 per-tado_x-entity rows: intersection of roomStatus.entity_ids\
      \ with config.tado_x_entities determines visible rows"
    - "A2 Option A/C: tado_x_entities visibility guard — frontend reads\
      \ backend-derived list; no direct entity registry access from JS"

key-files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/ws-client.ts
    - frontend/src/components/room-card.ts

key-decisions:
  - "matter_mappings?.[tadoId]?.[0] ?? '' used for current selection\
    \ (single Matter entity per row; schema stays a list per D-01)"
  - "Section heading 'Real-time calibration' chosen (Claude's Discretion)\
    \ for consistency with existing calibration terminology in the card"
  - "Intersection pattern for tado_x detection: entityIds.filter(id =>\
    \ tadoXEntities.includes(id)) — simple and data-driven from backend"

# Metrics
duration: ~10min
completed: 2026-06-03
---

# Phase 13 Plan 03: Matter Pairing UI — types + ws-client + room-card

**Matter entity type fields on ClimateConfig, setMatterMapping WS client
method, and per-tado_x-valve pairing section on the room card with
auto-save — completing the MCALIB-01 user-facing configuration surface.**

## Performance

- **Duration:** ~10 min
- **Started:** ~2026-06-03T14:45Z
- **Completed:** 2026-06-03T14:51Z
- **Tasks:** 2 code + 1 human checkpoint (pending)
- **Files modified:** 3

## Accomplishments

- Extended `ClimateConfig` in `types.ts` with three new optional fields:
  `matter_mappings?: Record<string, string[]>` (D-01 sparse schema),
  `matter_entities?: string[]` and `tado_x_entities?: string[]`
  (backend-derived read-only lists from plan 02 get_config extension)
- Added `WsClient.setMatterMapping(tadoEntityId, matterEntityIds)` method
  sending `climate_manager/set_matter_mapping` with D-15 payload shape;
  empty array removes the mapping
- Added `_renderMatterPairingSection()` to room-card.ts:
  - Intersects room's `entity_ids` with `config.tado_x_entities` for
    visibility guard — section hidden when room has no tado_x entities
  - Renders one row per tado_x entity: friendly name + native `<select>`
    populated from `config.matter_entities` with friendly names via
    `hass.states[id].attributes.friendly_name ?? id`
  - Includes `(none)` option at top; current selection from
    `matter_mappings?.[tadoId]?.[0] ?? ""`
  - Section heading: "Real-time calibration" with sub-label describing
    the sub-minute calibration purpose
- Added `_onMatterMappingChange(tadoEntityId, event)` auto-save handler:
  reads selected value, calls `ws.setMatterMapping`, then
  `panel.reloadConfig()` + `showToast("Saved")` — no Save button
- Composed `_renderMatterPairingSection()` into `render()` after the
  TRV section and pre-heat section
- TypeScript compiled clean; `make lint` passed after prettier auto-fix

## Task Commits

1. **Task 1: types.ts + ws-client.ts**
   - `bbd1cc2` feat(13-03): add matter mapping types and
     setMatterMapping WS method

2. **Task 2: room-card.ts Matter pairing section**
   - `0b6dc01` feat(13-03): add Matter pairing section to room card

## Files Created/Modified

- `frontend/src/types.ts` — Added `matter_mappings`, `matter_entities`,
  `tado_x_entities` to `ClimateConfig` interface with doc comments
- `frontend/src/ws-client.ts` — Added `setMatterMapping` method matching
  D-15 WS command payload schema
- `frontend/src/components/room-card.ts` — Added
  `_renderMatterPairingSection`, `_onMatterMappingChange`, and composed
  section into `render()` after `_renderPreheatSection()`

## Decisions Made

- **Section heading "Real-time calibration"** (Claude's Discretion):
  consistent with existing calibration terminology already used in the
  room card; sub-label clarifies the purpose of the pairing.
- **Single-entity picker** (current mapping reads `[0]`): each row shows
  one Matter entity drop-down per tado_x valve, matching the typical
  1:1 physical pairing; the schema remains a list per D-01.
- **Intersection for tado_x detection**: `roomStatus.entity_ids` filtered
  by `config.tado_x_entities` — clean, relies on backend-derived list
  (A2 Option A/C already resolved in plan 02).

## Deviations from Plan

None — plan executed exactly as written. Prettier reformatted the
room-card.ts additions during `make lint` (auto-fix, not a deviation).

## Checkpoint Status

**Task 3 (checkpoint:human-verify, gate=blocking):** PENDING human
visual verification. Awaiting `make build && make deploy` and live
panel inspection per the checkpoint instructions in 13-03-PLAN.md.

## Known Stubs

None — all data wires connect to backend-derived lists (`matter_entities`,
`tado_x_entities`, `matter_mappings`) surfaced by plan 02 get_config
extension.

## Threat Surface Scan

No new network endpoints introduced. UI options sourced exclusively from
`config.matter_entities` (backend-derived, platform-filtered); the WS
handler (plan 02) re-filters to `climate.*` server-side regardless of
what the UI sends (T-13-07 mitigated by defense-in-depth).

## Self-Check: PASSED

- `frontend/src/types.ts` contains `matter_mappings`, `matter_entities`,
  `tado_x_entities` fields
- `frontend/src/ws-client.ts` contains `setMatterMapping` method
- `frontend/src/components/room-card.ts` contains
  `_renderMatterPairingSection` and `_onMatterMappingChange`
- Commits `bbd1cc2` and `0b6dc01` exist in git log
- `npm run build` exits 0; `make lint` exits 0

---

*Phase: 13-matter-tado-x-real-time-calibration*
*Completed (partial — checkpoint pending): 2026-06-03*

---
phase: 06-zone-room-assignment-ui
plan: 03
subsystem: ui
tags: [lit, typescript, vite, room-card, person-card, zone-badge, zone-picker]

# Dependency graph
requires:
  - phase: 06-01
    provides:
      Zone WS methods + zone-tab component; ClimateConfig.zones and
      default_zone_name types in place
  - phase: 06-02
    provides:
      Zone data model storage; RoomConfig.zone_id field available from backend
provides:
  - Zone badge pill in every room-card collapsed header row showing current zone
    name
  - Zone <select> picker in every room-card expanded content below mode picker
  - _onZoneChange handler auto-saving zone assignment via ws.setRoomConfig
  - HA presence mode label renamed to "HA home tracking" in person-card badge +
    select option
affects: [06-zone-room-assignment-ui, future-room-card-extensions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zone badge uses secondary-background-color + divider-color pill matching
      program-badge visual weight without competing"
    - "Sparse zone_id model: empty-string select value maps to zone_id:
      undefined (Default Zone membership)"
    - "_getZoneName() defensive fallback: deleted zone_id reference falls back
      to default_zone_name then literal 'Default Zone'"
    - "Display-only label rename pattern: backend constant PRESENCE_MODE_HA='ha'
      unchanged; only UI text strings updated"

key-files:
  created: []
  modified:
    - frontend/src/components/room-card.ts
    - frontend/src/components/person-card.ts
    - custom_components/climate_manager/www/panel.js

key-decisions:
  - "Zone badge appended to existing .card-header-top row after program/period
    badges — no structural reorder needed"
  - "Zone picker placed immediately after mode picker, before persons section,
    per D-12"
  - "Empty select value ('') represents Default Zone membership; sent as
    zone_id: undefined to preserve sparse model (D-06 phase 4)"
  - "Defensive _getZoneName: if zone_id references a deleted zone, treats it as
    Default Zone to avoid broken UI"
  - "Display rename only: PRESENCE_MODE_HA constant and CSS class 'ha'
    unchanged; only text strings updated (D-13)"

patterns-established:
  - "Zone badge pattern: .zone-badge CSS class with neutral pill styling, fed by
    _getZoneName() helper"
  - "Zone picker pattern: reuses .select-wrapper / .select-label / .mode-select
    classes from existing mode picker"
  - "Sparse merge zone_id: newZoneId ? { zone_id: newZoneId } : { zone_id:
    undefined } — empty string = unset"

requirements-completed:
  - ASSIGN-02
  - ASSIGN-03
  - UI-06

# Metrics
duration: ~15min
completed: 2026-05-28
---

# Phase 06 Plan 03: Room-Card Zone Badge + Picker and Person-Card Label Rename Summary

**Zone badge pill and zone picker added to every room-card, and HA presence mode
display label renamed to "HA home tracking" in person-card — satisfying
ASSIGN-02, ASSIGN-03, UI-06, and D-13**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-28T (continuation agent)
- **Completed:** 2026-05-28
- **Tasks:** 2
- **Files modified:** 3 (room-card.ts, person-card.ts, panel.js rebuilt)

## Accomplishments

- Every room card now shows a zone badge pill in its collapsed header row with
  the current zone display name (or Default Zone fallback)
- Expanded room cards include a Zone `<select>` below the mode picker that
  auto-saves via `ws.setRoomConfig` with sparse-model `zone_id: undefined` for
  Default Zone
- `_getZoneName()` helper with defensive fallback handles deleted zone
  references gracefully
- "HA home tracking" display label replaces "HA" in both the person-card mode
  badge and mode select option; backend value `"ha"` is unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: room-card zone badge + zone picker + \_onZoneChange handler** -
   `62ebbab` (feat)
2. **Task 2: Rename "HA" -> "HA home tracking" in person-card.ts** - `b3ef0b5`
   (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `frontend/src/components/room-card.ts` - Added `.zone-badge` CSS,
  `_getZoneName()` helper, zone badge in header, Zone `<select>` picker in
  expanded content, `_onZoneChange` auto-save handler
- `frontend/src/components/person-card.ts` - Updated badge text and `<option>`
  text from "HA" to "HA home tracking" (2 line changes)
- `custom_components/climate_manager/www/panel.js` - Rebuilt Vite bundle (122
  kB)

## Decisions Made

- Zone badge appended after existing badges in `.card-header-top` — preserves
  room name, period, and program badges; no reorder
- Zone picker reuses `.select-wrapper` / `.select-label` / `.mode-select` CSS
  already defined for the room mode picker — visual consistency with zero new
  CSS
- Empty-string select value maps to `zone_id: undefined` patch to align with
  sparse-merge backend model (D-06 phase 4)
- `_getZoneName()` falls back through: zone_id lookup →
  `panelConfig.default_zone_name` → literal `"Default Zone"` — safe against
  stale zone_id references
- `persons-tab.ts` was not modified — badge rendering is fully delegated to
  `person-card.ts` via `<climate-manager-person-card>`, so UI-06 is satisfied
  without touching the tab

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ASSIGN-02, ASSIGN-03, UI-06, and D-13 are complete
- Room-card is now zone-aware end-to-end: badge display + picker save round-trip
- Person-card HA label matches user-visible terminology throughout the panel
- Ready for phase 06 verification / remaining plans in the
  zone-room-assignment-ui phase

---

_Phase: 06-zone-room-assignment-ui_ _Completed: 2026-05-28_

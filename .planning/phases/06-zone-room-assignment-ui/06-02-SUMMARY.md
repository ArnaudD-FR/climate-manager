---
phase: 06-zone-room-assignment-ui
plan: "02"
subsystem: frontend
tags: [lit, typescript, zone-management, tab-bar, ui]
dependency_graph:
  requires:
    - "06-01: WsClient zone methods (createZone, deleteZone, renameZone, ...) and climate-manager-zone-tab component"
  provides:
    - "main.ts dynamic zone tab-bar: Overview | Default Zone | [custom zones] | + | Rooms | Persons"
    - "_onCreateZone() handler with D-02 default naming and D-03 post-create name focus"
    - "_validateActiveTab() guard for stale zone UUIDs in localStorage (T-06-03)"
    - "<climate-manager-zone-tab> wired for both Default Zone and custom zones in _renderTabContent()"
  affects:
    - "06-03: room-card zone badge + zone picker — depends on zone tab rendering working in main.ts"
tech_stack:
  added: []
  patterns:
    - "post-load tab validation: _validateActiveTab() called after every _loadConfig() — guards T-06-03 localStorage tampering"
    - "dynamic tab enumeration: Object.entries(config.zones).map() in tab-bar render"
    - "zone_default / zone_<uuid> tab identity scheme for expandable tab namespace"
key_files:
  created: []
  modified:
    - frontend/src/main.ts
    - custom_components/climate_manager/www/panel.js
key_decisions:
  - "Tab identity scheme: 'zone_default' for Default Zone tab, 'zone_<uuid>' for custom zone tabs — static tabs remain 'global'/'rooms'/'persons'"
  - "_validateActiveTab() invoked inside _loadConfig() after every config reload (not just at startup) — ensures delete in zone-tab.ts triggers immediate fallback"
  - "Default Zone zoneConfig synthesized in-place from _config.global_mode + _config.global_time_program per Phase 4 D-02"
  - "Post-create focus uses .zone-name click() path to trigger zone-tab's _onNameClick handler (avoids duplicating focus logic)"
requirements-completed: [UI-01, UI-02, UI-03]
duration: ~10min
completed: "2026-05-28"
---

# Phase 6 Plan 02: Dynamic Zone Tabs in main.ts Summary

**Panel root gains dynamic zone tab-bar (Overview | Default Zone | custom zones | + | Rooms | Persons), _onCreateZone() with post-create name focus, and _validateActiveTab() localStorage guard wired to every config reload.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-05-28
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Tab-bar restructured to render Default Zone and all custom zones dynamically from `_config.zones`, with exact UI-01 / D-01 order
- `_onCreateZone()` computes "Zone N" name client-side, calls `createZone`, reloads config, switches tab, and focuses the name input (D-02, D-03)
- `_validateActiveTab()` rejects stale zone UUIDs and unknown values stored in localStorage — runs after every `_loadConfig()` call (T-06-03 mitigation)
- `_renderTabContent()` extended with `zone_default` and `zone_<uuid>` branches rendering `<climate-manager-zone-tab>` with synthesized or live `ZoneConfig`

## Task Commits

1. **Task 1: Dynamic zone tabs and + button in main.ts** - `0c4d56a` (feat)

## Files Created/Modified

- `frontend/src/main.ts` — Side-effect import for zone-tab.js, broadened `_activeTab` initializer, `_validateActiveTab()`, `_onCreateZone()`, rewritten tab-bar, extended `_renderTabContent()`, `.add-zone-btn` CSS
- `custom_components/climate_manager/www/panel.js` — Vite bundle updated (136.97 kB)

## Decisions Made

- `_validateActiveTab()` placed inside `_loadConfig()` (not just in `connectedCallback`) so every post-mutation config reload re-checks the active tab — this is essential for the delete flow in zone-tab.ts where the active zone can be deleted during the session.
- Default Zone `zoneConfig` is synthesized inline in `_renderTabContent()` rather than stored as a separate property — keeps the single source of truth in `_config` and avoids stale-prop issues.
- `_onCreateZone()` calls `_loadConfig()` (not `reloadConfig()`) directly to avoid triggering `_loadStatus()` unnecessarily during the create flow.

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing TypeScript errors in `frontend/src/components/time-bar.ts` (2 errors on `Period` discriminated union) were present before this plan and are out of scope. They did not prevent the Vite build from succeeding.

## Known Stubs

None. All zone rendering paths in main.ts are fully wired to real zone-tab.ts component and live WsClient methods.

## Threat Surface Scan

No new threat surface beyond the plan's threat model:
- T-06-03 (Tampering: localStorage "climate-manager-tab"): Mitigated — `_validateActiveTab()` falls back to "global" for any unknown or stale tab id; runs after every config reload.
- T-06-04 (DoS: rapid + button clicks): Accepted — no rate limiting added per plan disposition.
- T-06-SC: No new package installs.

## Self-Check: PASSED

- frontend/src/main.ts: FOUND
- custom_components/climate_manager/www/panel.js: FOUND (Vite build succeeded)
- Commit 0c4d56a (Task 1): verified via git log
- All acceptance criteria: PASSED (grep checks all returned expected matches)

## Next Phase Readiness

- Zone tab rendering in main.ts is complete; Plan 03 (room-card zone badge + zone picker) can proceed independently
- Zone creation, tab switching, and stale-UUID fallback are all wired and tested at build time

---
*Phase: 06-zone-room-assignment-ui*
*Completed: 2026-05-28*

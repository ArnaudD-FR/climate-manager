---
quick_id: 260521-ggx
slug: tab-persist-and-period-temp
date: 2026-05-21
commit: 5c57d2e
duration: ~5 minutes
files_modified:
  - frontend/src/main.ts
  - frontend/src/components/room-card.ts
  - custom_components/climate_manager/www/panel.js
status: complete
---

# Quick Task 260521-ggx: Tab Persistence + Period Temperature

## One-liner

localStorage tab persistence on refresh + room card header period chip now shows
full display name and temperature (e.g. "Normal · 20°C").

## What Was Done

### Task 1: Tab persistence (main.ts)

Replaced the static `@state() private _activeTab = "global"` initializer with an
IIFE that reads `localStorage.getItem("climate-manager-tab")` at construction
time. Valid tab names (`["global", "rooms", "persons"]`) are accepted; any
missing or invalid value falls back to `"global"`.

`_setTab(tab)` now writes to `localStorage.setItem("climate-manager-tab", tab)`
immediately after updating the reactive property, so the active tab survives a
page refresh.

### Task 2: Period display name + temperature (room-card.ts)

Added `PERIOD_DISPLAY_NAMES` to the existing import from `../types.js`.

`_renderHeaderStatus()` now resolves:

- `period` — raw `active_period` key (or `null`)
- `periodLabel` — mapped via `PERIOD_DISPLAY_NAMES`, falling back to the raw key
- `periodTempVal` — looked up from `panelConfig.period_temperatures[period]`
- `periodDisplay` — `"${periodLabel} · ${periodTempVal}°C"` when temperature is
  available, otherwise just the label

The clock chip in the room card header now reads e.g. "Normal · 20°C" instead of
"normal".

## Build

`cd frontend && npm run build` — 28 modules transformed, 0 errors, 0 warnings.

## Deviations

None — plan executed exactly as written.

## Self-Check

- [x] `frontend/src/main.ts` modified
- [x] `frontend/src/components/room-card.ts` modified
- [x] `custom_components/climate_manager/www/panel.js` rebuilt
- [x] Commit `5c57d2e` exists

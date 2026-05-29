---
quick_id: 260520-nn9
slug: order-rooms-tab-by-floor-then-room-name
date: 2026-05-20
status: complete
commits:
  - 57532b2
  - eabaffb
files_modified:
  - frontend/src/types.ts
  - frontend/src/components/rooms-tab.ts
  - custom_components/climate_manager/www/panel.js
---

# Quick Task 260520-nn9: Order Rooms Tab by Floor then Room Name — Summary

**One-liner:** Floor-grouped room ordering with floor name section headers using
hass.areas and hass.floors, sorted by floor.level then display name.

## What Was Done

### Task 1: Extend Hass interface (commit 57532b2)

Added `areas` and `floors` fields to the `Hass` TypeScript interface in
`frontend/src/types.ts`:

- `areas: Record<string, { area_id: string; name: string; floor_id: string | null }>`
- `floors: Record<string, { floor_id: string; name: string; level: number }>`

### Task 2: Rewrite rooms-tab sort logic (commit eabaffb)

Replaced the custom-program-first sort in `frontend/src/components/rooms-tab.ts`
with floor-based grouping:

- Builds a `Map<string | null, string[]>` from floor_id to room ID arrays using
  `hass.areas[roomId].floor_id`
- Sorts each group alphabetically by display name (status name or formatted
  area_id fallback)
- Sorts non-null floor IDs by `hass.floors[fid].level` ascending
- Renders floor section headers (`.floor-header` div) before each floor group
- Floorless rooms (null floor_id) rendered last with no header
- Added `.floor-header` CSS rule matching the spec

### Task 3: Build

`make build` succeeded — 27 modules transformed, no TypeScript errors. Output:
`panel.js` 91.81 kB.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/types.ts` — modified with areas/floors fields
- `frontend/src/components/rooms-tab.ts` — modified with floor grouping logic
- Commits 57532b2 and eabaffb exist in git log
- Build output `custom_components/climate_manager/www/panel.js` regenerated
  successfully

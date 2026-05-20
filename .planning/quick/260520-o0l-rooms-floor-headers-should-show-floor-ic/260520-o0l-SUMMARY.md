---
quick_id: 260520-o0l
slug: rooms-floor-headers-should-show-floor-ic
date: 2026-05-20
status: complete
commits:
  - 1057fec
files_modified:
  - frontend/src/types.ts
  - frontend/src/components/rooms-tab.ts
  - custom_components/climate_manager/www/panel.js
---

# Quick Task 260520-o0l: Rooms Floor Headers Should Show Floor Icon — Summary

**One-liner:** Floor section headers now show a ha-icon derived from floor.level (or the floor's configured icon if set).

## What Was Done

### Task 1: Extend Hass floors type
Added `icon?: string | null` to the `floors` record type in `frontend/src/types.ts`.

### Task 2: Floor header icon rendering
In `frontend/src/components/rooms-tab.ts`:
- Added `getFloorIcon(fid)` helper: returns `floor.icon` if set, else maps level → MDI icon (`mdi:home-floor-b` for negative, `mdi:home-floor-0` for 0, `mdi:home-floor-1/2/3` for upper floors)
- Updated `.floor-header` CSS to `display: flex; align-items: center; gap: 6px`
- Added `ha-icon` CSS with `--mdc-icon-size: 16px`
- Rendered `<ha-icon icon=${getFloorIcon(fid)}>` before the floor name

### Task 3: Build and deploy
Build succeeded (92.46 kB). Deployed to homeassistant.local.

## Deviations from Plan

None.

## Self-Check: PASSED

- Commit 1057fec in git log
- Build output regenerated successfully

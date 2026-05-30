---
quick_id: 260528-z4k
slug: zone-tab-assigned-rooms-sort-by-floor
status: complete
date: 2026-05-28
commit: 2f9e72b
---

# Quick Task 260528-z4k: Zone tab assigned rooms sorted by floor then name

Sorted assigned room chips in zone-tab by floor (descending level, upper floors first), then alphabetically by name — matching rooms-tab ordering.

Changes in `frontend/src/components/zone-tab.ts`:
- Added `_getSortedAssignedRoomGroups()` helper: groups rooms by `hass.areas[id].floor_id`, sorts within each floor alphabetically, orders floors by `hass.floors[fid].level` descending (same logic as rooms-tab)
- Added `_getFloorIcon()` helper (mirrors rooms-tab's equivalent)
- Added `.floor-group-label` CSS (smaller variant of rooms-tab `.floor-header`)
- Updated `render()`: replaced flat chip list with grouped chips, each group preceded by a floor label (no label for floorless rooms); "Add room" search-picker moved to its own chips row at the bottom

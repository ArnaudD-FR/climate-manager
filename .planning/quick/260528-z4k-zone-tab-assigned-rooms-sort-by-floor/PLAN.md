---
quick_id: 260528-z4k
slug: zone-tab-assigned-rooms-sort-by-floor
status: in_progress
date: 2026-05-28
---

# Quick Task 260528-z4k: Zone tab assigned rooms sorted by floor then name

## Goal
Sort assigned rooms in zone-tab by floor (descending level, upper floors first), then alphabetically by name within each floor — matching the rooms-tab ordering.

## Implementation
File: `frontend/src/components/zone-tab.ts`

1. Add `_getSortedAssignedRoomGroups()` helper returning `Array<{floorId: string|null, floorName: string, roomIds: string[]}>`
2. Add `.floor-group-label` CSS matching rooms-tab's `.floor-header` style
3. Update render: replace flat `assignedRoomIds.map(...)` with grouped chips per floor

## Sorting logic (same as rooms-tab)
- Group by `hass.areas[roomId].floor_id` (null = floorless)
- Within each floor: `.sort((a,b) => name(a).localeCompare(name(b)))`
- Floor order: by `hass.floors[fid].level` descending (upper floors first)
- Floorless rooms at end, no header

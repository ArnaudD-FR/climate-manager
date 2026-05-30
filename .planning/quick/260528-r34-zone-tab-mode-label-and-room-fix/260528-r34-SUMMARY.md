---
quick_id: 260528-r34
slug: zone-tab-mode-label-and-room-fix
status: complete
date: 2026-05-28
commit: 4ed289c
---

# Quick Task 260528-r34: Zone tab mode label + assigned rooms bug fix

Two changes in one commit:

1. **Label rename**: "Zone mode" → "Mode" with `section-label` CSS class (uppercase, bold, small) — matches "Assigned rooms" section heading style.

2. **Bug fix**: Zone-tab `_getAssignedRoomIds()` and `_getUnassignedRoomItems()` previously iterated only over `config.rooms` (rooms with any saved config). Rooms with all-default settings had no `config.rooms` entry, making them invisible to zone management. Fixed by:
   - Adding `status: StatusPayload | null` prop to zone-tab
   - Adding `_allRoomIds()` helper that uses `status.rooms_status` (filtered to TRV rooms) as the complete room universe, falling back to `config.rooms` keys when status is unavailable
   - Passing `.status=${this._status}` to zone-tab in main.ts (both default and custom zone renders)

Files changed: `frontend/src/components/zone-tab.ts`, `frontend/src/main.ts`, `custom_components/climate_manager/www/panel.js`

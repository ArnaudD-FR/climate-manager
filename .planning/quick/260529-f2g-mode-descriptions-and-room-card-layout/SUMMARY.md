---
slug: f2g
status: complete
---

All changes applied and deployed.

- **zone-tab**: `_renderModeDescription()` below mode select (3 variants: off/time_program/time_program_presences); removed old `_renderScheduleHint()` and call
- **room-card**: `_renderRoomModeDescription()` below mode select (3 variants); Zone section moved above Schedule; `_renderTrvSection()` rewritten as read-only chips + `hass-more-info` dispatch on click; removed `_renderCustomScheduleHint()`
- **person-card**: inline description paragraph below presence mode select (4 variants); removed schedule-hint below time-bar

Commit: a425c41

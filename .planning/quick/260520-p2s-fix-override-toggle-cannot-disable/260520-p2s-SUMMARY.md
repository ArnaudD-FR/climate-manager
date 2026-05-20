---
quick_id: 260520-p2s
slug: fix-override-toggle-cannot-disable
date: 2026-05-20
status: complete
commits:
  - eb4760c
files_modified:
  - frontend/src/types.ts
  - frontend/src/components/room-card.ts
  - custom_components/climate_manager/www/panel.js
---
# Quick Task 260520-p2s: Fix Override Toggle Cannot Disable — Summary

Root cause: `null ?? undefined` evaluates to `undefined`, which JSON serialization drops from
the config object. Backend received `config: {}`, `.update({})` was a no-op, time_program was
never cleared.

Fixed by removing `?? undefined` in `_onOverrideToggle` so `null` is sent explicitly, and
widening `RoomConfig.time_program` type to `DailyProgram | null`. Backend's `.update({"time_program": None})` now correctly clears the field. Build succeeded, deployed.

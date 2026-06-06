---
quick_id: 260520-s9s
slug: remove-sensors-section-from-room-card-an
date: 2026-05-20
status: complete
commits:
  - f09eb50
files_modified:
  - frontend/src/components/room-card.ts
  - frontend/src/types.ts
  - custom_components/climate_manager/websocket.py
  - custom_components/climate_manager/coordinator.py
---

# Quick Task 260520-s9s: Remove sensors section from room card + fix backend priority chain — Summary

Removed the manual sensor picker UI added in 260520-t4u (wrong approach — sensor
configuration belongs in HA area settings). Updated backend to use
`AreaEntry.temperature_entity_id` / `humidity_entity_id` as primary sensor
source, with `room_auto_sensors` fallback and TRV `current_temperature` as last
resort. Both `ws_get_status` and `_build_status_payload` updated consistently.
Added `unavailable`/`unknown` state guards for sensor readings. Deployed to
homeassistant.local.

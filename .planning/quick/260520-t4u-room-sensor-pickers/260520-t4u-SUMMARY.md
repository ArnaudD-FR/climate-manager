---
quick_id: 260520-t4u
slug: room-sensor-pickers
date: 2026-05-20
status: complete
commits:
  - 0802014
files_modified:
  - frontend/src/components/room-card.ts
  - frontend/src/types.ts
---
# Quick Task 260520-t4u: Room Sensor Pickers — Summary

Added a "Sensors" section to the room card expanded body with two text inputs:
- Temperature sensor entity ID
- Humidity sensor entity ID

Both fields save on blur via `ws.setRoomConfig` + `panel.reloadConfig()`. Empty field
sends `null` to the backend, which falls back to auto-detected sensors (from
`room_auto_sensors`) or the TRV `current_temperature` attribute. Updated
`RoomConfig.temperature_sensor` and `.humidity_sensor` types to `string | null`
to allow explicit clearing. Build succeeded, deployed.

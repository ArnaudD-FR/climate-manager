---
quick_id: 260525-trv
slug: trv-rooms-only-filter
date: 2026-05-25
status: in_progress
---

# Quick Task: TRV rooms only — filter chaudière from rooms & persons tabs

## Goal

Rooms that have only boiler/chaudière climate entities (no `current_temperature`
attribute) must be excluded from:

1. The Rooms tab room list
2. The Persons tab room choices picker

## Detection strategy

A room is a "TRV room" if any of its climate entities has `current_temperature`
in its state attributes.

- Tado X Smart Radiator Thermostats: always have `current_temperature`
- Tado Extension Kit (chaudière relay): does NOT have `current_temperature`
- HA preserves last-known attributes on unavailable state, so offline TRVs stay
  tagged correctly

## Changes

### 1. `custom_components/climate_manager/websocket.py`

- In `ws_get_status`, compute `has_trv = any(entity has current_temperature)`
- Add `room_entry["has_trv"] = has_trv`

### 2. `custom_components/climate_manager/coordinator.py`

- Same in `_build_status_payload()`

### 3. `frontend/src/types.ts`

- Add `has_trv?: boolean` to `RoomStatus`

### 4. `frontend/src/components/rooms-tab.ts`

- Filter `statusRooms` to `.filter(r => r.has_trv !== false)` before building
  `allRoomIds`

### 5. `frontend/src/components/persons-tab.ts`

- Same filter in `_getRoomChoices()`

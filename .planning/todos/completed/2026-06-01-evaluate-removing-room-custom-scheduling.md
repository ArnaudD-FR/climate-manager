---
created: 2026-06-01T00:00:00.000Z
title: Remove room custom scheduling — superseded by zones
area: ui
files:
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/coordinator.py
  - frontend/src/components/rooms-tab.ts
---

## Problem

Room-level custom scheduling (`room_mode: custom` + per-room `time_program`)
was introduced before zones existed. It no longer makes sense: zones already
allow defining different schedules and associating rooms to them. A user who
wants a room on a different schedule just creates a zone for it — which is
cleaner, named, and visible in the panel. The custom-schedule path is now a
parallel mechanism that does the same thing with more hidden complexity.

Having both paths adds UI surface, coordinator branching, and test burden for
no additional capability.

## Solution

Remove `room_mode: custom` entirely:
1. Drop the custom schedule editor from the Rooms tab
2. Simplify coordinator: remove the `ROOM_MODE_CUSTOM` branch
3. Storage migration: convert any existing custom-scheduled rooms to a new
   dedicated single-room zone with the same schedule
4. Update requirements docs and tests accordingly

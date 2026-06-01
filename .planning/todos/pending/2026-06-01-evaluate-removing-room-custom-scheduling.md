---
created: 2026-06-01T00:00:00.000Z
title: Evaluate removing room custom scheduling (duplicated by zones)
area: ui
files:
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/coordinator.py
  - frontend/src/components/rooms-tab.ts
---

## Problem

Room-level custom scheduling (`room_mode: custom` + per-room `time_program`)
was introduced before zones existed. Now that every room belongs to a zone
with its own weekly program, the custom schedule per room feels redundant:
users can achieve the same result by creating a dedicated zone for that room.
Having both paths adds UI surface, coordinator complexity, and test coverage
burden for a feature that may no longer earn its keep.

## Solution

1. Audit whether any meaningful use case exists that zones cannot cover
   (e.g. a single-room zone is functionally identical to a custom schedule)
2. If no unique value: deprecate `room_mode: custom` — remove the custom
   schedule editor from the Rooms tab, simplify coordinator branching, and
   add a migration that converts existing custom-scheduled rooms to a
   dedicated single-room zone
3. If there is a unique use case: document it and close this todo

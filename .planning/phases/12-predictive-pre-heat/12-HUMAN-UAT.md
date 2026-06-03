---
status: diagnosed
phase: 12-predictive-pre-heat
source: [12-VERIFICATION.md]
started: 2026-06-02T18:55:00Z
updated: 2026-06-03T00:00:00Z
---

## Current Test

[human UAT session completed — 1 design issue found]

## Tests

### 1. Pre-heating status line renders during active pre-heat
expected: When a room is pre-heating, the room card shows
  "Pre-heating (→ XX.X°C)" with the actual target temperature
result: [skipped — pre-heat toggle design issue found first; blocked
  on design resolution before visual scenarios are meaningful]

### 2. Suppression warning conditional rendering
expected: "Pre-heat disabled — presence cannot be scheduled" appears
  only when preheat_enabled=true AND preheat_suppressed=true (ha-mode
  only room); not shown when pre-heat is simply disabled
result: [skipped — blocked on design resolution]

### 3. Max lead time input visibility toggle
expected: The max lead time number input appears only when the Pre-heat
  checkbox is checked; hidden when unchecked
result: issue — Pre-heat toggle (preheat_enabled) is scoped per room
  but should be per zone. User confirmed during panel inspection that
  the toggle granularity is wrong: all rooms in a zone should share a
  single pre-heat on/off setting, not each room independently.

## Summary

total: 3
passed: 0
issues: 1
pending: 0
skipped: 2
blocked: 0

## Gaps

### GAP-01: preheat_enabled should be per zone, not per room
status: failed
requirement: PREHEAT-01
description: >
  The pre-heat enable/disable toggle is currently on RoomConfig
  (preheat_enabled per room). User UAT revealed it should live on
  ZoneConfig instead — all rooms in a zone share one pre-heat on/off.
  preheat_max_lead_minutes may also need to move to ZoneConfig or be
  handled at zone level.
impact: >
  All three visual scenarios are blocked on this design correction.
  The backend coordinator, websocket layer, frontend types, and
  room-card UI all need updating to read/write zone-level preheat
  config instead of room-level.
fix: >
  Move preheat_enabled (and likely preheat_max_lead_minutes) from
  RoomConfig to ZoneConfig. Update: storage migration, websocket
  ws_set_room_config → new ws_set_zone_preheat_config or extend
  ws_set_zone_config, coordinator _async_preheat_room to read zone
  config, frontend types.ts, and room-card.ts toggle rendering.

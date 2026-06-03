---
created: 2026-05-31T15:01:52
title: Map Matter devices to Tado X sensors for real-time calibration
area: calibration
files:
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/trv.py
---

## Problem

Tado X free tier refreshes cloud data every ~45 minutes. The TRV
auto-calibration loop runs every minute but temperature readings only
change every 45 min, making calibration effectively coarse-grained.
This significantly limits the value of the auto-calibration feature
for free-tier users.

## Solution

Map Matter TRV devices (which update temperature in real-time via local
push) to their corresponding Tado X physical valve devices in the same
room. When a Matter device's current_temperature changes, use it as the
TRV temperature input for calibration instead of waiting for the 45-min
Tado X cloud fetch. This would give sub-minute calibration responsiveness
even on the free tier.

Implementation hints:
- Maintain a user-configurable room-level mapping: Matter entity → Tado X
  device serial
- Subscribe to state_changed events for mapped Matter entities
- When a mapped Matter entity fires state_changed with a new
  current_temperature, immediately trigger _async_calibrate for that room
- Fall back to existing Tado X zone entity temperature when no Matter
  mapping exists
- UI: add mapping table in Global Settings calibration section

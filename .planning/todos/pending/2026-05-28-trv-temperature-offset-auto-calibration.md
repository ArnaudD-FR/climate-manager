---
created: 2026-05-28T18:50:22Z
title: TRV temperature offset auto-calibration from room sensor
area: general
files:
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/discovery.py
  - custom_components/climate_manager/trv.py
---

## Problem

When a room has a third-party temperature sensor (e.g., a dedicated Aqara/Zigbee sensor) that is more accurate than the TRV's built-in sensor, the TRV's reported temperature can drift from the real room temperature. This causes Climate Manager to push the wrong setpoints (the TRV compensates internally but its display and `current_temperature` are off).

Some TRVs (e.g., ha-tado-x via `tado_x.set_temperature_offset`) support a temperature offset that can be adjusted programmatically. Climate Manager already discovers room sensors (`discover_room_sensors`) and has access to both the TRV's `device_temperature` sensor and the room reference sensor.

## Solution

Add a global option (e.g., in global settings) to enable automatic TRV offset calibration:
- When enabled, Climate Manager periodically compares the room's reference sensor temperature against the TRV's measured temperature (`sensor.*_device_temperature` or `attributes.current_temperature`)
- Computes the delta and calls the appropriate offset service (e.g., `tado_x.set_temperature_offset`) if the TRV/integration supports it
- Guard: only apply when the TRV advertises support (detect by checking if the offset service or a `temperature_offset` attribute is available)
- Configurable: smoothing/averaging to avoid jitter; min delta threshold before applying a correction

Context from investigation (2026-05-28):
- ha-tado-x exposes `sensor.*_device_temperature` (raw) and `sensor.*_temperature_offset` per device, all under the same `device_id` as the `climate.*` entity — linkable via entity registry
- ha-tado-x has an open bug (#51): `set_temperature_offset` silently fails in some versions
- Better Thermostat and Smart Offset Thermostat HACS integrations do this generically but wrap the climate entity, conflicting with Climate Manager's direct control model
- Blueprint approach is an alternative that avoids wrapping

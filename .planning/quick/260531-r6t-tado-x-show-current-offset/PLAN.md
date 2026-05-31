---
id: 260531-r6t
slug: tado-x-show-current-offset
status: in-progress
---

# Show current TRV temperature offset for Tado X devices

For each Tado X Radiator Valve X device in the calibration table, show
the offset currently applied on the device.

## Priority logic

1. If `coordinator._calibration_last_offset[device_id]` exists →
   climate_manager has set an offset this session; show that value.
2. Otherwise → read from `sensor.vanne_<name>_temperature_offset`
   (translation_key="temperature_offset", platform="tado_x",
   same device_id).

## Changes

- `websocket.py`: look up offset sensor entity per device_id in the
  entity registry, compute `current_offset`, add to each Tado X TRV row.
- `types.ts`: add `current_offset: number | null` to `TRVCalibrationEntry`.
- `global-settings-tab.ts`: add "Current offset" column to calib table.

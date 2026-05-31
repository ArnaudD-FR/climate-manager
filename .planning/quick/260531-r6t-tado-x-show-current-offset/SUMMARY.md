---
id: 260531-r6t
status: complete
---

# Summary

Added "Current offset" column to calibration table for Tado X devices.

## Changes

- `websocket.py`: for each Radiator Valve X device, computes `current_offset`:
  - `_calibration_last_offset[device_id]` if climate_manager set one this session
  - Otherwise finds `sensor.*_temperature_offset` via entity registry
    (`translation_key="temperature_offset"`, `platform="tado_x"`, same `device_id`)
  - Non-Tado-X rows get `current_offset: None`
- `types.ts`: added `current_offset: number | null` to `TRVCalibrationEntry`
- `global-settings-tab.ts`: added "Current offset" column (colspan updated 6→7)

## Commit

68e61f0

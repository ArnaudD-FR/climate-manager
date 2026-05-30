---
id: 260530-p4r
status: complete
---

# Summary

Split TRV calibration table by floor, sorted by friendly name within each floor.

## Changes

- `websocket.py`: added `area_id` to each TRV dict in `get_calibration_status`
- `types.ts`: added `area_id: string` to `TRVCalibrationEntry`
- `global-settings-tab.ts`: grouped TRVs by `hass.areas[area_id].floor_id`,
  sorted each group by `friendly_name`, rendered floor section headers
  (icon + name in a `colspan=6` table row). Floor IDs sorted by `level`
  ascending. Floorless TRVs rendered at end with no header.

## Commit

8123a22 (amended into fix(09): add TRV temp and room temp columns)

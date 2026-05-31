---
id: 260531-any
status: complete
---

# Summary

Removed the "Last applied delta" column from the calibration table.
Now that "Current offset" shows the actual device offset, the delta
column was redundant.

## Changes

- `websocket.py`: removed `last_applied_delta` key from both per-TRV
  response dicts (Tado X valve devices and non-Tado X entities);
  removed the field from the docstring
- `types.ts`: removed `last_applied_delta: number | null` from
  `TRVCalibrationEntry`
- `global-settings-tab.ts`: removed `<th>Last applied delta</th>` from
  thead; removed the `<td>` cell rendering `trv.last_applied_delta`;
  updated floor header colspan from 7 → 6

## Commit

392e8e4

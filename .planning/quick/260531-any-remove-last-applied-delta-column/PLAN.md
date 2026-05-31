---
id: 260531-any
status: in-progress
---

# Remove "Last applied delta" column from calibration table

## Goal

Remove the "Last applied delta" column from the TRV calibration table.
Now that "Current offset" shows the actual device offset, the "Last applied
delta" column (the calculated correction from the last calibration run) is
redundant and clutters the table.

## Scope

- `frontend/src/components/global-settings-tab.ts` — remove `<th>` header
  and `<td>` data cell for `last_applied_delta`; update `colspan` on floor
  headers from 7 to 6
- `frontend/src/types.ts` — remove `last_applied_delta` field from
  `TRVCalibrationEntry` interface
- `custom_components/climate_manager/websocket.py` — remove
  `last_applied_delta` key from the per-TRV dict in `ws_get_calibration_status`
- Build + deploy

## Tasks

1. Edit `frontend/src/components/global-settings-tab.ts`:
   - Remove `<th>Last applied delta</th>` (or similar) from thead
   - Remove the `<td>` cell rendering `trv.last_applied_delta` from tbody rows
   - Change colspan on floor group headers from 7 → 6
2. Edit `frontend/src/types.ts`:
   - Remove `last_applied_delta: number | null;` from `TRVCalibrationEntry`
3. Edit `custom_components/climate_manager/websocket.py`:
   - Remove `"last_applied_delta": ...` from the per-TRV response dict
4. Run `make build && make deploy`
5. Commit

## Files

- `frontend/src/components/global-settings-tab.ts`
- `frontend/src/types.ts`
- `custom_components/climate_manager/websocket.py`

---
quick_id: 260530-m8u
slug: trv-calibration-card-enhancement
title: TRV Auto-Calibration card enhancement
date: 2026-05-30
status: complete
commit: e52c674
---

# Summary

Renamed the Global Settings "Options" card to "TRV Auto-Calibration" and
expanded it with a per-TRV status table (visible only when calibration is
enabled).

## Changes

- **coordinator.py**: Added `_calibration_last_changed: dict[str, str]`;
  records ISO UTC timestamp after each successful `set_trv_offset` call.
- **websocket.py**: Added `get_calibration_status` WS command (read-only);
  returns per-TRV dict with entity_id, friendly_name, supports_calibration,
  current_temperature, current_offset, last_calibrated_at.
- **types.ts**: Added `TRVCalibrationEntry` interface.
- **ws-client.ts**: Added `getCalibrationStatus()` method.
- **global-settings-tab.ts**: Renamed card, shortened toggle label, added
  `_renderTRVTable()` with support badges, temp/offset column, last-adjusted
  column, and a Refresh button; table auto-loads when calibration is enabled.

## Tests

153 passed, 1 pre-existing unrelated failure
(test_phase06_acceptance.py — HA fixture issue, not caused by this change).

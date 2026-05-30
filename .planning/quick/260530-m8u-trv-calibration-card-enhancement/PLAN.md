---
quick_id: 260530-m8u
slug: trv-calibration-card-enhancement
title: TRV Auto-Calibration card enhancement
date: 2026-05-30
status: in_progress
---

# TRV Auto-Calibration Card Enhancement

Rename the "Options" card, adjust toggle label, and add a per-TRV status table
(visible only when calibration is enabled) showing: friendly name, calibration
support, current temperature + offset, last calibrated timestamp.

## Tasks

1. coordinator.py — add `_calibration_last_changed` dict; record timestamp after
   successful `set_trv_offset` call
2. websocket.py — add `get_calibration_status` WS command factory; register it
3. types.ts — add `TRVCalibrationEntry` interface
4. ws-client.ts — add `getCalibrationStatus()` method
5. global-settings-tab.ts — rename card, adjust label, add status table + CSS
6. Build and deploy

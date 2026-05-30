---
id: 260530-p4r
slug: trv-table-floor-grouping
title: TRV calibration table — floor grouping and name sort
date: 2026-05-30
status: in_progress
---

# TRV calibration table — floor grouping and name sort

Split the TRV calibration status table by floor (like rooms-tab) and sort
rows by TRV friendly name within each floor section.

## Tasks

1. websocket.py — add `area_id` to each TRV dict in get_calibration_status
2. types.ts — add `area_id: string` to TRVCalibrationEntry
3. global-settings-tab.ts — group by floor, sort by name, floor headers
4. Build, deploy, amend commit

## Implementation notes

- Mirror rooms-tab floor grouping: `hass.areas[trv.area_id]?.floor_id`
- Sort each floor group by `friendly_name.localeCompare()`
- Sort floor IDs by `hass.floors[fid].level` ascending
- Floorless TRVs at end, no section header
- Floor header CSS already exists in rooms-tab; replicate in global-settings-tab
- Table structure preserved — floor headers appear as full-width rows above tbody
  sections (or use separate tbody per floor with a thead-like floor-header row)

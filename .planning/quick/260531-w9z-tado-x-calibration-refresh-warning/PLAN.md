---
id: 260531-w9z
slug: tado-x-calibration-refresh-warning
status: in-progress
---

# Tado X calibration refresh warning banner

When at least one TRV in the calibration table uses the Tado X integration
(`supports_calibration: true`), show a small info banner above the table
explaining the cloud refresh rate and the time the data was last fetched.

## Changes

- `frontend/src/components/global-settings-tab.ts`:
  - Add `@state() _calibrationFetchedAt: Date | null` — set on every
    successful `_loadCalibrationStatuses` call.
  - In `_renderTRVTable`: detect Tado X presence via
    `_trvStatuses.some(t => t.supports_calibration)`.
  - Render an info banner with refresh-rate note + "Last fetched: HH:MM:SS".
  - Add `.calib-info-banner` CSS.

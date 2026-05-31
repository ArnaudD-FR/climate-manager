---
id: 260531-w9z
status: complete
---

# Summary

Added a Tado X cloud refresh-rate info banner to the calibration table.

## Changes

- `frontend/src/components/global-settings-tab.ts`:
  - Added `@state() _calibrationFetchedAt: Date | null` — set on every
    successful load of calibration statuses.
  - Banner is shown when `_trvStatuses.some(t => t.supports_calibration)`
    (i.e., at least one Tado X Radiator Valve X device is present).
  - Banner reads: "Tado X data is fetched from the cloud every ~30 s —
    displayed temperatures may lag slightly behind actual values."
  - Sub-line shows "Last fetched: HH:MM:SS" using `toLocaleTimeString()`.
  - Added `.calib-info-banner` and `.calib-info-fetched` CSS styles.

## Commit

b656fd7

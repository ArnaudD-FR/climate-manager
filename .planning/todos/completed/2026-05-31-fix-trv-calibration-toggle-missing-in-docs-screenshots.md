---
created: 2026-05-31T13:50:35.379Z
title: Fix TRV calibration toggle missing in docs screenshots
area: docs
files:
  - docs/screenshots/
  - custom_components/climate_manager/www/panel.js
---

## Problem

The TRV auto-calibration enable/disable toggle is not visible in the
documentation screenshots. Screenshots were likely captured before the
calibration toggle UI was added, so the docs don't reflect the current
panel state.

## Solution

Run `make screenshots` to recapture up-to-date panel screenshots that
include the calibration toggle, then commit the updated images.

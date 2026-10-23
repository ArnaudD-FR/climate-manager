---
created: 2026-10-23T00:00:00
title: Rename "calibration" to "sensor alignment" (recalage) everywhere
area: backend, ui, docs
files:
  - custom_components/climate_manager/calibration.py
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/__init__.py
  - custom_components/climate_manager/room.py
  - custom_components/climate_manager/websocket.py
  - custom_components/climate_manager/vendors/base.py
  - custom_components/climate_manager/vendors/__init__.py
  - custom_components/climate_manager/vendors/tado_x.py
  - frontend/src/components/global-settings-tab.ts
  - frontend/src/components/room-card.ts
  - frontend/src/types.ts
  - frontend/src/ws-client.ts
  - docs/architecture.md
  - README.md
  - tests/test_calibration.py
  - tests/test_calibration_preheat.py
  - tests/test_coordinator.py
  - tests/test_preheat.py
  - tests/test_room_domain.py
  - tests/test_vendor_tado_x.py
  - tests/test_websocket.py
status: pending
---

## Problem

"Calibration" overstates what the feature does: the TRV is not calibrated,
it is only asked to follow the room sensor (its temperature offset is set to
the gap between the room sensor and the TRV reading, in steady conditions).
The user chose the name **recalage** (2026-10-23): "Recalage sur le capteur"
in French, **sensor alignment** in English (code, logs and the panel, which
is English-only until i18n — see deferred multi-language todo).

## Solution

Rename everything, not only the labels:

- Module `calibration.py` → `alignment.py`; `Calibrator` → `SensorAligner`
  (or similar); `CalibrationTarget`, `calibration_targets`,
  `supports_calibration`, `log_calibration`, listener names.
- Logs: `calibrate | …` → `align | …`.
- WS commands: `climate_manager/get_calibration_status` and
  `climate_manager/set_calibration_config` → `…/get_alignment_status`,
  `…/set_alignment_config`; payload fields to match. Frontend and server
  ship together, no need to keep the old names.
- Stored config keys `calibration_enabled` and `calibration_threshold` →
  `alignment_enabled`, `alignment_threshold`: needs a storage migration
  (bump the minor version, copy the old keys, drop them).
- Panel: section title, toggle, threshold, room-card rows and hints.
- Tests (rename the files too), `docs/architecture.md`, README, panel
  screenshots (`make screenshots`).
- Check with `grep -rni calibrat` that only the migration still uses the
  old words.

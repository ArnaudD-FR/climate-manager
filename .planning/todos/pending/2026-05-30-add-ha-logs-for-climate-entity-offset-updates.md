---
created: 2026-05-30T13:15:16.286Z
title: Add HA logs for climate entity offset updates
area: general
files:
  - custom_components/climate_manager/coordinator.py
---

## Problem

The calibration engine (added in phase 09-02) applies TRV temperature offset
corrections silently. There is no log entry when an offset is updated, making
it impossible to observe calibration activity in HA logs or debug incorrect
offsets in production. Users and developers cannot tell when an offset was
last applied, to which entity, or what the old/new values were.

## Solution

Add `_LOGGER.info(...)` calls in the coordinator's calibration code whenever
an offset update is issued:

- Log the entity_id of the climate entity whose offset changed
- Log the old offset value and the new offset value
- Log the reason (delta, reference sensor entity_id)

Also consider a `_LOGGER.debug(...)` for skipped updates (delta below
threshold) to aid debugging without polluting info logs.

Context: calibration engine lives in
`custom_components/climate_manager/coordinator.py` (added in commit e1ca3ca).

---
created: 2026-06-02T19:46:46.038Z
title: Add log traces for presence and heating state changes
area: general
files:
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/schedule.py
---

## Problem

Currently there is no structured logging when presence or heating state
changes. Hard to diagnose why a room/zone is at a certain temperature or
why it changed — requires inferring from HA logs without clear markers.

Three categories of events need log traces:

1. **Person presence** — when a person transitions present → absent or
   absent → present, log who changed and what triggered it (schedule
   tick, HA device tracker, manual override).

2. **Zone heating state** — when a zone changes its heating mode or
   active state, log the zone name, old state, new state, and the reason
   (global mode change, presence change, schedule slot boundary).

3. **Room heating temperature** — when a room's target temperature is
   set on the TRV, log the room name, new target temp, and the decision
   path that produced it (which schedule slot, which zone, which person
   presence state drove it).

## Solution

Add `_LOGGER.debug(...)` / `_LOGGER.info(...)` calls at the state
transition points in `coordinator.py` and `schedule.py`. Use a consistent
format:

```
[climate_manager] presence | person=<name> home=<bool> reason=<source>
[climate_manager] zone     | zone=<name> state=<old>→<new> reason=<why>
[climate_manager] heating  | room=<name> temp=<T>°C zone=<zone> slot=<slot>
```

Log level: `debug` for individual TRV calls, `info` for presence/zone
state transitions (visible at default HA log level).

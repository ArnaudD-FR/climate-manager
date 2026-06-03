---
created: 2026-06-03T17:15:26.414Z
title: Consolidate default zone keys into top-level default_zone ZoneConfig
area: general
files:
  - custom_components/climate_manager/const.py:220
  - custom_components/climate_manager/coordinator.py:965
  - custom_components/climate_manager/storage.py
  - custom_components/climate_manager/websocket.py
---

## Problem

The Default Zone is currently split across several top-level storage keys
(`global_mode`, `global_time_program`, `default_zone_name`,
`default_zone_preheat_enabled`) rather than being a first-class `ZoneConfig`
object. Custom zones already use a unified `ZoneConfig` shape
`{name, mode, time_program, preheat_enabled}`.

This inconsistency forces the coordinator's `_resolve_zone_config` to
special-case the Default Zone, and WebSocket handlers maintain separate
code paths for reading/mutating global vs. zone config.

## Solution

1. Add a top-level `default_zone` key to `DEFAULT_CONFIG` and the storage
   schema, shaped as a full `ZoneConfig`:
   ```
   "default_zone": {
     "name": "Home",
     "mode": "time_program",
     "time_program": { ...default daily program... },
     "preheat_enabled": false
   }
   ```
2. Migrate storage load in `ClimateManagerStore.async_load()`: if the stored
   data has the old flat keys (`global_mode`, `global_time_program`, etc.),
   promote them into `default_zone` and drop the flat keys.
3. Update `_resolve_zone_config` in coordinator to read Default Zone from
   `config["default_zone"]` instead of `config["global_mode"]` /
   `config["global_time_program"]`.
4. Update all WebSocket handlers that currently read/write `global_mode`,
   `global_time_program`, `default_zone_name`, `default_zone_preheat_enabled`
   — unify them with the zone handlers where possible.
5. Keep backward-compatible wire names in the WS API if the panel uses
   `global_mode` today, or update the panel types/ws-client in the same pass.
6. Remove the now-redundant flat top-level keys from `DEFAULT_CONFIG`.

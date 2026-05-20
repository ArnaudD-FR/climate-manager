---
quick_id: 260520-m0t
status: complete
date: 2026-05-20
commit: ff842bd
---

## Summary

Fixed `discover_rooms` in `discovery.py` to include climate entities whose
**device** is assigned to an HA area (device-level area assignment). The previous
implementation only checked direct entity-level assignment via
`get_entries_for_area_id`, which returns nothing when the entity's `area_id` is
`None` (i.e., the entity inherits its area from its device). Most HA users assign
areas at the device level, so the Rooms tab showed "No rooms discovered" for all
correctly-configured setups.

## Root Cause

`entity_reg.entities.get_entries_for_area_id(area_id)` only matches
`entity.area_id == area_id`. For device-level assignment, `entity.area_id is None`
and the effective area is `device_reg.devices.get(entity.device_id).area_id`.

## Fix

Two-pass discovery:
1. Pass 1 — direct entity assignment (existing logic)
2. Pass 2 — device-level assignment: for entities where `entity.area_id is None`
   and `entity.device_id` is set, look up `device.area_id`

Added `from homeassistant.helpers import device_registry as dr`.

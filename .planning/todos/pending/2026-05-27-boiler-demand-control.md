---
created: 2026-05-27T00:00:00.000Z
title: Boiler demand control - start/stop boiler based on TRV heating demand
area: general
files:
  - custom_components/climate_manager/trv.py:21
  - custom_components/climate_manager/coordinator.py
---

## Problem

The boiler currently runs independently of whether any room actually needs heat.
Climate Manager should start the boiler when at least one room in a zone is calling
for heat, and stop it when all rooms are satisfied — avoiding unnecessary boiler cycles
and improving energy efficiency.

## TRV Feedback — valve position vs hvac_action

Valve opening % is **not part of the standard HA `climate` entity spec**. It is
exposed differently per brand/integration:

| Source | Attribute/Entity | Notes |
|--------|-----------------|-------|
| Zigbee2mqtt TRVs | `sensor.*_pi_heating_demand` (0–100%) | ZigBee cluster 0x0201 attr 0x0008 — most reliable |
| Tado | `sensor.*_heating_power` | Separate sensor entity |
| Z-Wave | non-standard attribute on climate entity | varies by device |
| Generic climate | `hvac_action` (`"heating"` / `"idle"`) | Binary only — no percentage |

`hvac_action` is binary and only tells us *whether* the TRV is calling for heat, not
*how much*. A room at 5% valve is treated the same as one at 100%.

## Solution

**Per-room optional valve position entity:**
- Each room config gains an optional `valve_position_entity: str | null` field
  pointing to a sensor that exposes 0–100% valve opening
- When set, the coordinator reads this sensor for precise demand signal
- When null, falls back to `hvac_action` for binary demand detection

**Boiler demand logic (per zone):**

```
def room_demands_heat(room) -> bool:
    if room.valve_position_entity:
        position = float(hass.states.get(room.valve_position_entity).state)
        return position > VALVE_DEMAND_THRESHOLD  # e.g. > 5%
    else:
        action = hass.states.get(room.trv_entity).attributes.get("hvac_action")
        return action == "heating"

zone_demands_heat = any(room_demands_heat(r) for r in zone.rooms)

turn_on(zone.boiler_entity) if zone_demands_heat else turn_off(zone.boiler_entity)
```

**Boiler entity control:**
- If `boiler_entity` is a `switch` → `switch.turn_on` / `switch.turn_off`
- If `boiler_entity` is a `climate` entity → `climate.set_hvac_mode("heat")` / `("off")`

**Evaluation timing:**
- Demand is checked at each coordinator evaluation cycle
- Configurable debounce delay (default 3 min) prevents boiler flapping when rooms
  hover near their target temperature
- Pre-heat: boiler stays on while any TRV reports demand during pre-heat window

**Fallback chain (no valve_position_entity, no hvac_action):**
- Compare `current_temperature` vs `target_temperature`:
  if `current < target - 0.5°C` → assume heating demand

**Boiler status in UI:**
- Room card and zone card should display boiler on/off state when a boiler is
  declared for the zone
- Could reuse the `preheat_active` status mechanism from the pre-heat todo

**Minor version bump** — additive, depends on boiler-declaration-per-zone todo.

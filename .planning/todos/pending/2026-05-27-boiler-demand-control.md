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

## TRV Feedback — hvac_action

The standard HA `climate` entity exposes an `hvac_action` attribute that answers
exactly this question:

| hvac_action | Meaning |
|-------------|---------|
| `"heating"` | TRV valve is open, actively calling for heat from the boiler |
| `"idle"`    | Room is at target temperature, no heat demand |
| `"off"`     | Entity is off |

This attribute is already part of the HA climate entity standard — no brand-specific
API needed. Support varies by TRV model: most modern TRVs (Tado, Danfoss Ally, etc.)
report it correctly. Some cheaper models may not implement it reliably.

## Solution

**Boiler demand logic (per zone):**

```
zone_demands_heat = any(
    hass.states.get(trv_entity).attributes["hvac_action"] == "heating"
    for trv_entity in zone.room_trv_entities
)

if zone_demands_heat:
    turn_on(zone.boiler_entity)
else:
    turn_off(zone.boiler_entity)
```

**Boiler entity control:**
- If `boiler_entity` is a `switch` → `switch.turn_on` / `switch.turn_off`
- If `boiler_entity` is a `climate` entity → `climate.set_hvac_mode("heat")` / `("off")`
- The `boiler_declaration-per-zone` todo already establishes the `boiler_entity`
  field per zone; this todo adds the demand-driven control logic on top of it

**Evaluation timing:**
- `hvac_action` is checked at each coordinator evaluation cycle
- TRVs may take 1–5 min to update `hvac_action` after a setpoint change — a
  configurable debounce delay (e.g. 3 min) prevents the boiler from flapping
  on/off rapidly when rooms hover near their target temperature
- Pre-heat window: during active pre-heat the demand logic still applies — boiler
  stays on as long as at least one room's TRV reports `hvac_action == "heating"`

**Fallback:**
- If a TRV does not expose `hvac_action` (attribute missing or always `None`),
  fall back to comparing `current_temperature` vs `target_temperature` as a proxy:
  if `current < target - 0.5°C` → assume heating demand

**Boiler status in UI:**
- Room card and zone card should display boiler on/off state when a boiler is
  declared for the zone
- Could reuse the `preheat_active` status mechanism from the pre-heat todo

**Minor version bump** — additive, depends on boiler-declaration-per-zone todo.

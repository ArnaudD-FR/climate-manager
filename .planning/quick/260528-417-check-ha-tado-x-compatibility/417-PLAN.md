---
quick_id: 260528-417
slug: check-ha-tado-x-compatibility
description: checks if ha-tado-x is compatible
date: 2026-05-28
status: complete
---

# Quick Task 417: checks if ha-tado-x is compatible

## Goal

Determine whether the `ha-tado-x` integration
(https://github.com/exabird/ha-tado-x) is compatible with Climate Manager —
specifically: can its `climate.*` entities be discovered, controlled, and held
correctly by Climate Manager?

## Investigation Plan

1. Read `ha-tado-x/custom_components/tado_x/climate.py` — entity definition,
   supported features, HVAC modes, service handlers
2. Read Climate Manager discovery logic (`discovery.py`) — what it expects from
   climate entities
3. Read Climate Manager TRV control logic (`trv.py`) — what service calls it
   issues
4. Read Climate Manager coordinator (`coordinator.py`) — D-02/D-03
   push-on-change and manual override hold logic
5. Cross-reference: identify any mismatches or limitations

## Files to Check

- `https://github.com/exabird/ha-tado-x` — `climate.py`, `const.py`
- `custom_components/climate_manager/discovery.py`
- `custom_components/climate_manager/trv.py`
- `custom_components/climate_manager/coordinator.py`

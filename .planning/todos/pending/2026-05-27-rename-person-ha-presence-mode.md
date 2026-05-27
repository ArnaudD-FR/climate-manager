---
created: 2026-05-27T00:00:00.000Z
title: Rename "ha" person presence mode to a clearer label in the UI
area: ui
files:
  - custom_components/climate_manager/const.py:132
  - custom_components/climate_manager/coordinator.py:156
---

## Problem

Each person has a presence mode in the Persons tab. The four options are:
- `scheduled` — use the person's configured weekly schedule
- `force_present` — always treat as present
- `force_absent` — always treat as absent
- `ha` — delegate to HA's `person.*` entity (live device tracker)

The `ha` label is opaque in the UI. Users don't know what "HA" means in this context
without reading documentation. It could mean "Home Assistant default", "HA entity",
or something else entirely.

## Solution

Rename the `ha` mode display label in the UI (the internal identifier can stay `ha`
if no config migration is needed). Candidate labels:

| Candidate | Clarity |
|-----------|---------|
| `ha` | current — cryptic |
| `Home Assistant` | explicit but generic |
| `HA tracker` | better — implies device tracking |
| `Live detection` | describes behaviour, not the source |
| `HA person entity` | most explicit — matches the HA concept |
| `Automatic (HA)` | friendly + source hint |

Recommended: **"HA person entity"** or **"Live detection (HA)"** — open for decision
before implementing.

This is a UI-only label change if the internal `mode: "ha"` string is kept as-is in
the config store. No migration needed in that case.

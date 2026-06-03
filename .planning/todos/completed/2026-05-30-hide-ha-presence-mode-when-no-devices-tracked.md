---
created: 2026-05-30T08:26:17.776Z
title: Hide HA presence mode when person has no tracked device in HA
area: ui
files:
  - frontend/src/components/persons-tab.ts
  - custom_components/climate_manager/websocket.py
---

## Problem

The person presence mode picker in the Persons tab always shows "HA" (live
device tracking) as an available option, even for persons who have no device
tracker associated in HA. Selecting it for such a person will never reflect
true presence — `hass.states['person.X'].state` stays at `not_home` or
`unknown` permanently, which silently breaks heating logic.

## Solution

Filter the available mode options based on whether the HA `person.*` entity
has any linked device trackers. The presence of device trackers can be inferred
from `hass.states['person.X'].attributes.source_type` or by checking if
`hass.states['person.X']` transitions at all (or via
`attributes.device_trackers` if available).

Two possible approaches:
1. **Frontend**: in the mode picker, only render the "HA" option when
   `hass.states[personId]?.attributes?.device_trackers?.length > 0`
2. **Backend**: include a `has_device_tracker: bool` flag in the
   `get_status` persons payload so the frontend doesn't need to inspect
   raw `hass.states`

Approach 2 is cleaner for the frontend but requires a backend change.
Approach 1 is simpler and entirely frontend-side.

See also: [[rename-person-ha-presence-mode]] — related todo about
clarifying the label for the `ha` mode.

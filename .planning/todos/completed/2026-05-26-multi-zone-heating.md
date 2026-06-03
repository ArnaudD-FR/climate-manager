---
created: 2026-05-26T20:58:08.747Z
title: Define multiple heating zones with independent modes
area: general
resolves_phase: 4
files: []
---

## Problem

All rooms currently share a single global heating mode and time program. Users
want to group rooms into named zones (e.g. "Bathrooms") that can have their own
mode and schedule — independently from the global config and from other zones.

Use case: a "Bathrooms" zone uses Comfort mode and continues heating even when
the rest of the house is switched Off.

## Solution

TBD — likely involves:

- A new "zones" concept in the data model (name, list of rooms, mode override,
  optional schedule)
- UI to create/edit zones and assign rooms to them
- Schedule evaluation engine respects zone overrides before falling back to
  global mode
- Zones can be On/Comfort/Reduced/Off independently; global mode applies to
  rooms not in any zone

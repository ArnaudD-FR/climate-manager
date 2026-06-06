---
created: 2026-05-27T00:00:00.000Z
title: Per-zone boiler declaration with shared boiler support
area: general
files: []
status: deferred
deferred_to: v1.4+ (per-zone boiler / flow-temp normalisation)
---

## Problem

The pre-heat feature (see adaptive-pre-heat todo) requires knowing the boiler's
supply (flow) temperature to normalise room inertia across outdoor conditions. A
home may have multiple zones served by different boilers (e.g. underfloor
heating on one circuit, radiators on another), so boiler association must be per
zone, not global.

A single boiler can serve multiple zones simultaneously (e.g. ground floor +
first floor on the same circuit).

## Solution

**Data model — zone config gains `boiler_entity`:**

```
zone:
  name: str
  boiler_entity: str | null   # HA climate or sensor entity_id for this zone's boiler
  rooms: list[str]
  ...
```

- `boiler_entity` points to a HA `climate` entity (reads `current_temperature`
  as flow temp) or a `sensor` entity exposing supply temperature directly
- Multiple zones can reference the same `boiler_entity` — the integration reads
  it once per evaluation cycle regardless of how many zones reference it
- `null` means no boiler declared for this zone; pre-heat falls back to a
  user-configured fixed flow temperature assumption (configurable at zone level)

**Relationship to global outdoor temperature:**

- Outdoor temperature (`outdoor_temp_entity`) remains a single global config —
  there is one outdoor sensor for the whole home
- Boiler entity is zone-level because different heating circuits may have
  different boilers with different heat curves

**UI — Zones tab:**

- Each zone config section gains a "Boiler entity" field (entity picker,
  optional)
- If multiple zones share the same boiler, each independently references it by
  entity_id — no explicit "shared" declaration needed in the UI

**Impact on pre-heat todo:**

- Supersedes the `boiler_entity` field proposed as global config in the adaptive
  pre-heat todo — that field moves to zone config instead
- `preheat_flow_temp_ref` (normalisation reference temperature) also moves to
  zone config since different boilers may have different reference temps

**Minor version bump** — additive, no breaking changes to existing zone config
(new optional field, defaults to null).

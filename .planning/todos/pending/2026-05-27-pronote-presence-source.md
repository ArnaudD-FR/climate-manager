---
created: 2026-05-27T00:00:00.000Z
title: Pronote scheduling source for automatic presence from school timetable
area: general
files: []
---

## Problem

Parents want presence to be derived automatically from a child's school
timetable rather than maintained manually. Pronote is the dominant French school
management platform.

## Solution

- New optional `schedule_source` field on person config: "manual" (default) |
  "pronote"
- Pronote source: stores credentials (URL, username, password) in person config;
  fetches timetable via `pronotepy` (external PyPI dep — requires HACS
  requirements entry; breaks v1 "no external deps" constraint → separate minor
  release)
- Caches fetched timetable with TTL; maps school slots → absent, free/holiday →
  present
- Falls back to manual schedule on fetch failure
- Additive: existing manual scheduling is unaffected
- Defer to its own minor release after even/odd week scheduling ships

## Notes

- `pronotepy` reverse-engineers the Pronote protocol — maintenance risk if
  Pronote changes their API
- Introduces first external PyPI dependency; must be declared in manifest.json
  `requirements` and tested for HACS compatibility

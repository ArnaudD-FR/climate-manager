---
slug: e8f
title: Section help tooltips and schedule behavior hints
status: in_progress
created: 2026-05-29
---

## Goal

Add contextual help to card sections:
1. Short tooltip (native `title` attr) on every `section-label` element
2. When a scheduling component (time-bar) is visible, show a `.schedule-hint` paragraph below it describing how the system will behave given the current mode

## Files to change

- `frontend/src/shared-styles.ts` — add `.schedule-hint` CSS
- `frontend/src/components/zone-tab.ts` — tooltips + schedule hint below time-bar
- `frontend/src/components/room-card.ts` — tooltips + schedule hint below custom time-bar
- `frontend/src/components/person-card.ts` — tooltips + hint below presence schedule

## Tasks

- [ ] Add `.schedule-hint` CSS to shared-styles.ts
- [ ] Update zone-tab.ts: add `title` to Mode/Assigned rooms labels; add dynamic schedule hint below time-bar based on zoneConfig.mode
- [ ] Update room-card.ts: add `title` to all section labels; add schedule hint below custom time-bar based on global mode
- [ ] Update person-card.ts: add `title` to Presence mode/Room associations/Presence schedule labels; add hint below presence time-bar
- [ ] Build and verify

## Schedule hint copy

**zone-tab — off:** "Zone is off — the schedule is saved but not applied. All assigned rooms use frost protection only."

**zone-tab — time_program:** "Rooms in this zone follow this schedule. Each period sets the target temperature for all assigned rooms."

**zone-tab — time_program_presences:** "Rooms heat according to this schedule only when an assigned person is present. When everyone is absent, rooms stay at Reduced temperature. A Reduced or Frost period sandwiched between two Normal/Comfort periods is held at the preceding Normal/Comfort temperature while someone is present."

**room-card custom — time_program:** "This room follows its own custom schedule, overriding the zone program."

**room-card custom — time_program_presences:** "This room follows its own custom schedule. Normal and Comfort periods apply only when an assigned person is present — otherwise the room stays at Reduced temperature."

**room-card custom — off:** "Zone is in Off mode. The schedule is saved but not applied."

**person-card presence schedule:** "Defines when this person is considered present. Active in Time & presence mode only — Scheduled periods marked Present enable heating for this person's assigned rooms."

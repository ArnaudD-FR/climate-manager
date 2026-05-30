---
slug: f2g
title: Mode descriptions below selects, room-card layout fixes, read-only entities
status: in_progress
created: 2026-05-29
---

## Changes

### person-card.ts
- Add description paragraph below the presence mode select (not above)
- Remove the inline schedule-hint below the presence time-bar

### zone-tab.ts
- Add description paragraph below the mode select
- Remove _renderScheduleHint() and its call

### room-card.ts
- Add description paragraph below the room mode select
- Remove _renderCustomScheduleHint() and its call
- Move Zone section ABOVE the custom schedule section
- Replace hui-thermostat-card grid with read-only entity chips (hass-more-info on click)

## Mode description copy

zone-tab:
- off: "Zone is off. All assigned rooms are kept at frost protection temperature only."
- time_program: "Rooms follow the weekly schedule. Each period sets the target temperature for all assigned rooms."
- time_program_presences: "Rooms heat according to the schedule only when an assigned person is present. When everyone is absent, rooms stay at Reduced temperature."

room-card:
- global: "This room follows the zone's heating schedule."
- custom: "This room uses its own custom schedule, independent of the zone."
- frost_protection: "Heating is disabled. The room is kept at frost protection temperature only."

person-card:
- scheduled: "Presence follows a weekly schedule. Edit the schedule below."
- ha: "Presence mirrors Home Assistant's home/away tracking for this person."
- force_present: "This person is always considered present, regardless of schedule or location."
- force_absent: "This person is always considered absent. Their rooms will not be heated for their presence."

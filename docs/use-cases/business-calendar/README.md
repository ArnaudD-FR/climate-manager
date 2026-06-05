# Noah — Business Calendar

Noah works from a dedicated home office and attends meetings or travels
frequently. Rather than encoding a fixed schedule he delegates his presence
entirely to a calendar entity: whenever `calendar.work_meetings` has an active
event, he is treated as away. This scenario showcases the **calendar** presence
mode and two-zone layout — the Home Office sits in its own **Office** zone with
a work-hours heating programme, while the Bedroom and Living Room follow the
**Home** Default Zone domestic programme. **Both zones are
`time_program_presences`** — the same calendar drives presence for all three
rooms. When a meeting or travel event is active Noah counts as away and every
room sets back to reduced; when the calendar is clear he is present and both
zones' schedules apply normally.

## Household layout

| Room        | Zone        | Floor        | Heats when                        |
| ----------- | ----------- | ------------ | --------------------------------- |
| Home Office | Office      | First Floor  | Work-hours comfort — Noah present |
| Bedroom     | Home (Def.) | First Floor  | Domestic programme — Noah present |
| Living Room | Home (Def.) | Ground Floor | Domestic programme — Noah present |

## Zone configuration

| Zone        | Mode                     | Programme                                 |
| ----------- | ------------------------ | ----------------------------------------- |
| Home (Def.) | `time_program_presences` | Domestic day/night (normal/frost)         |
| Office      | `time_program_presences` | Work-hours comfort (08:00–18:00 weekdays) |

Both zones are presence-driven. A room in either zone only heats to its
scheduled period when Noah is present (calendar shows no active event). When an
event is active all his rooms set back to Reduced regardless of which zone they
are in.

## Presence configuration

Noah uses **mode: calendar**.

| Setting         | Value                                       |
| --------------- | ------------------------------------------- |
| Calendar entity | `calendar.work_meetings`                    |
| Event means     | absent — an active event means Noah is away |
| Gap handling    | `day_span` — absent for the whole event day |
| Wake-up advance | 30 minutes                                  |

`wakeup_advance_minutes: 30` shifts Noah's calendar-derived presence to begin 30
minutes before the **first calendar event of the day** so his rooms are warm
before his first meeting — not a return-home mechanism.

No schedule time-bar editor is shown for calendar-mode persons; the panel
instead renders the calendar configuration selectors (entity picker, event
meaning, gap handling, and wake-up advance).

## Rooms driven by Noah

Noah's `room_ids` are **home_office**, **bedroom**, and **living_room**. All
three rooms need an assigned person because both zones are
`time_program_presences` — a room with no assigned person in a presences zone
would never heat to its scheduled period.

| Room        | Zone   | Tracked for presence |
| ----------- | ------ | -------------------- |
| Home Office | Office | yes                  |
| Bedroom     | Home   | yes                  |
| Living Room | Home   | yes                  |

When the calendar shows no active event Noah is present and all three rooms
reflect a person count of 1 and heat according to their zone schedule.

## Screenshots

### Overview

![Overview — Noah present, two zones](screenshots/overview.png)

The Overview shows two zone pills — Home (Default Zone) and Office (custom zone)
— both in `time_program_presences` mode, each with its current active period;
Noah is listed as present.

### Rooms

![Rooms tab — rooms grouped by zone](screenshots/rooms.png)

The Rooms tab groups Home Office under the Office zone badge and Bedroom plus
Living Room under the Home zone badge. All three rooms show a person count of 1
because Noah is present.

### Persons

![Persons tab — Noah card expanded](screenshots/persons.png)

The expanded Noah card shows the calendar configuration panel: entity selector,
event-means toggle, gap-handling selector, and wake-up advance field (30 min),
plus the three room chips (Home Office, Bedroom, Living Room) grouped by floor.

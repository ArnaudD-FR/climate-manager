# Noah — Business Calendar

Noah works from a dedicated home office and attends meetings or travels
frequently. Rather than encoding a fixed schedule he delegates his presence
entirely to a calendar: whenever the **Work Meetings** calendar has an active
event, he is treated as away. This scenario showcases the **Calendar** presence
mode and two-zone layout — the Home Office sits in its own **Office** zone with
a work-hours heating programme, while the Bedroom and Living Room follow the
**Home** Default Zone domestic programme. **Both zones are Time program &
presences** — the same calendar drives presence for all three rooms. When a
meeting or travel event is active Noah counts as away and every room sets back
to Reduced; when the calendar is clear he is present and both zones' schedules
apply normally.

## Household layout

| Room        | Zone        | Floor        | Heats when                        |
| ----------- | ----------- | ------------ | --------------------------------- |
| Home Office | Office      | First Floor  | Work-hours comfort — Noah present |
| Bedroom     | Home (Def.) | First Floor  | Domestic programme — Noah present |
| Living Room | Home (Def.) | Ground Floor | Domestic programme — Noah present |

## Zone configuration

| Zone        | Mode                     | Programme                                 |
| ----------- | ------------------------ | ----------------------------------------- |
| Home (Def.) | Time program & presences | Domestic day/night (normal/frost)         |
| Office      | Time program & presences | Work-hours comfort (08:00–18:00 weekdays) |

Both zones are presence-driven. A room in either zone only heats to its
scheduled period when Noah is present (calendar shows no active event). When an
event is active all his rooms set back to Reduced regardless of which zone they
are in.

## Presence configuration

Noah uses **Calendar** presence mode.

| Setting              | Value                                |
| -------------------- | ------------------------------------ |
| Calendar source      | Work Meetings                        |
| Absent during events | an active event means Noah is away   |
| Gap handling         | Absent all day (first to last event) |
| Wake-up advance      | 30 minutes                           |

The **Wake-up advance** of 30 minutes shifts Noah's calendar-derived presence to
begin 30 minutes before the **first calendar event of the day** so his rooms are
warm before his first meeting — not a return-home mechanism.

No schedule time-bar editor is shown for Calendar-mode persons; the panel
instead renders the calendar configuration selectors (calendar source picker,
**Absent during events** / **Present during events** toggle, gap-handling
selector, and **Wake-up advance** field).

## Rooms driven by Noah

Noah has **Home Office**, **Bedroom**, and **Living Room** in his **Room
associations**. All three rooms need an assigned person because both zones are
**Time program & presences** — a room with no assigned person in a presences
zone would never heat to its scheduled period.

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
— both in **Time program & presences** mode, each with its current active
period; Noah is listed as present.

### Rooms

![Rooms tab — rooms grouped by zone](screenshots/rooms.png)

The Rooms tab groups Home Office under the Office zone badge and Bedroom plus
Living Room under the Home zone badge. All three rooms show a person count of 1
because Noah is present.

### Persons

![Persons tab — Noah card expanded](screenshots/persons.png)

The expanded Noah card shows the calendar configuration panel: calendar source
selector, **Absent during events** toggle, gap-handling selector, and **Wake-up
advance** field (30 min), plus the three room chips (Home Office, Bedroom,
Living Room) grouped by floor.

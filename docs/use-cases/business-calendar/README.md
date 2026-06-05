# Noah — Business Calendar

Noah works from a dedicated home office and attends meetings or travels
frequently. Rather than encoding a fixed schedule he delegates his presence
entirely to a calendar entity: whenever `calendar.work_meetings` has an active
event, he is treated as away. This scenario showcases the **calendar** presence
mode and two-zone layout — the Home Office sits in its own **Office** zone with
a work-hours heating programme, while the shared living areas follow the
standard **Home** Default Zone.

## Household layout

| Room        | Zone         | Floor        | Heats when                            |
| ----------- | ------------ | ------------ | ------------------------------------- |
| Home Office | Office       | First Floor  | Work-hours comfort + reduced evenings |
| Bedroom     | Default Zone | First Floor  | Residential programme + Noah present  |
| Living Room | Default Zone | Ground Floor | Residential programme                 |

## Presence configuration

Noah uses **mode: calendar**.

| Setting         | Value                                       |
| --------------- | ------------------------------------------- |
| Calendar entity | `calendar.work_meetings`                    |
| Event means     | absent — an active event means Noah is away |
| Gap handling    | `day_span` — absent for the whole event day |
| Wake-up advance | 60 minutes (pre-heat bedroom before return) |

No schedule time-bar editor is shown for calendar-mode persons; the panel
instead renders the calendar configuration selectors (entity picker, event
meaning, gap handling, and wake-up advance).

## Rooms driven by Noah

Noah's `room_ids` are **home_office** and **bedroom**. When the calendar shows
no active event he is present, and both rooms reflect a non-zero person count.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Home Office | yes                  |
| Bedroom     | yes                  |
| Living Room | no (zone-only)       |

## Screenshots

### Overview

![Overview — Noah present, two zones](screenshots/overview.png)

The Overview shows two zone pills — Home (Default Zone) and Office (custom zone)
— each with its current active period; Noah is listed as present.

### Rooms

![Rooms tab — rooms grouped by zone](screenshots/rooms.png)

The Rooms tab groups Home Office under the Office zone badge and Bedroom plus
Living Room under the Home zone badge, illustrating how a custom zone segments a
household.

### Persons

![Persons tab — Noah card expanded](screenshots/persons.png)

The expanded Noah card shows the calendar configuration panel instead of a
schedule grid: entity selector, event-means toggle, gap-handling selector, and
wake-up advance field, plus the two room chips (Home Office, Bedroom) grouped by
floor.

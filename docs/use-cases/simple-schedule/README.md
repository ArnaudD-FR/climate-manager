# Emma — Simple Schedule

Emma lives alone in a two-storey house and follows a standard office week. She
leaves for work every weekday morning and returns in the late afternoon, while
weekends are entirely hers at home. This scenario shows the simplest possible
Climate Manager setup: a **single Default Zone** in **Time program & presences**
mode, four rooms, and one person on a **Scheduled** / **Single week** presence
programme.

The zone is **presence-driven**: rooms follow the time-program schedule while
Emma is home and fall back to Reduced while she is at work (09:00–17:30). She is
present overnight — "absent" only covers the hours she is physically out of the
house.

The screenshots are pinned to **Wednesday at 19:00** — Emma returned home at
17:30, so all four rooms are heating to Normal.

## Household layout

| Room        | Zone         | Floor        | Heats when                       |
| ----------- | ------------ | ------------ | -------------------------------- |
| Living Room | Default Zone | Ground Floor | Zone schedule while Emma is home |
| Kitchen     | Default Zone | Ground Floor | Zone schedule while Emma is home |
| Bedroom     | Default Zone | First Floor  | Zone schedule while Emma is home |
| Home Office | Default Zone | First Floor  | Zone schedule while Emma is home |

## Presence configuration

Emma uses **Scheduled** presence mode with a **Single week** schedule — the same
pattern repeats every week with no alternation.

### Schedule

| Day     | Present                        | Absent      |
| ------- | ------------------------------ | ----------- |
| Mon–Fri | 00:00–09:00, 17:30 to midnight | 09:00–17:30 |
| Sat–Sun | all day (00:00 onwards)        | —           |

Emma is present overnight. She is marked absent only during the hours she is
physically away at work (09:00–17:30 on weekdays).

## Rooms driven by Emma

Emma's **Room associations** cover **all four rooms**: Bedroom, Home Office,
Living Room, and Kitchen. Because the zone is **Time program & presences**,
every room needs at least one assigned person to receive scheduled heat. All
four rooms show a person count of 1/1 when Emma is home.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Bedroom     | yes                  |
| Home Office | yes                  |
| Living Room | yes                  |
| Kitchen     | yes                  |

## Screenshots

### Overview

![Overview — Emma present, single zone](screenshots/overview.png)

The Overview tab shows one zone row: Home in **Time program & presences** mode
with active period **Normal**, and Emma listed as currently present (green dot).
The Temperatures panel below confirms the four period setpoints (Frost
protection 7°C, Reduced 16°C, Normal 20°C, Comfort 22°C).

### Rooms

![Rooms tab — all four rooms in Default Zone](screenshots/rooms.png)

All four rooms appear grouped by floor — Bedroom and Home Office on the First
Floor, Kitchen and Living Room on the Ground Floor — each showing a **Normal ·
20°C** badge, the Home zone chip, live temperature and humidity, and a 1/1
person count confirming Emma is present.

### Persons

![Persons tab — Emma card expanded](screenshots/persons.png)

The expanded Emma card shows her **Single week** presence schedule: every
weekday row carries an identical Present/Absent/Present pattern (absent
09:00–17:30), while Saturday and Sunday are fully present. Room associations
appear below the schedule, grouped by floor: Bedroom and Home Office on the
First Floor, Kitchen and Living Room on the Ground Floor.

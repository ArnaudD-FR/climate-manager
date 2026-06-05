# Lena — Student Mixed Schedule

Lena is a university student whose lecture timetable changes every day of the
week: Monday is a long day of back-to-back sessions, Tuesday has a late-morning
slot only, Wednesday is the heaviest day, Thursday is a short morning, and
Friday finishes early afternoon. Weekends she is home all day. This scenario
demonstrates how a **Scheduled** / **Single week** presence programme can
express genuinely varied per-weekday absent blocks rather than a simple
repeating pattern.

The zone is **presence-driven** (**Time program & presences**): all three rooms
follow the time-program schedule while Lena is home and fall back to Reduced
while she is at her lectures. She is present overnight — "absent" only covers
the hours she is physically at university.

## Household layout

| Room        | Zone         | Floor        | Heats when                       |
| ----------- | ------------ | ------------ | -------------------------------- |
| Bedroom     | Default Zone | First Floor  | Zone schedule while Lena is home |
| Study       | Default Zone | First Floor  | Zone schedule while Lena is home |
| Living Room | Default Zone | Ground Floor | Zone schedule while Lena is home |

## Presence configuration

Lena uses **Scheduled** presence mode with a **Single week** schedule.

### Schedule

| Day | Present                        | Absent      |
| --- | ------------------------------ | ----------- |
| Mon | 00:00–08:00, 16:00 to midnight | 08:00–16:00 |
| Tue | 00:00–10:00, 13:00 to midnight | 10:00–13:00 |
| Wed | 00:00–08:00, 18:00 to midnight | 08:00–18:00 |
| Thu | 00:00–09:00, 12:00 to midnight | 09:00–12:00 |
| Fri | 00:00–08:00, 14:00 to midnight | 08:00–14:00 |
| Sat | all day (00:00 onwards)        | —           |
| Sun | all day (00:00 onwards)        | —           |

Lena is present overnight. She is marked absent only during the hours she is
physically at university.

## Rooms driven by Lena

Lena's **Room associations** cover **all three rooms**: Bedroom, Study, and
Living Room. Because the zone is **Time program & presences**, every room needs
at least one assigned person to receive scheduled heat. All three rooms show a
non-zero person count when Lena is home.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Bedroom     | yes                  |
| Study       | yes                  |
| Living Room | yes                  |

## Screenshots

### Overview

![Overview — Lena present, single zone](screenshots/overview.png)

The Overview shows the single Home zone in **Time program & presences** mode
with the active period and Lena listed as currently present; all three rooms
show a non-zero person count.

### Rooms

![Rooms tab — all three rooms in Default Zone](screenshots/rooms.png)

All three rooms appear under the Default Zone group with live temperature and
humidity readings, illustrating a single-zone presence-driven household.

### Persons

![Persons tab — Lena card expanded](screenshots/persons.png)

The expanded Lena card highlights the per-day time bars: each weekday row shows
a distinct pattern of absent blocks reflecting the varying class timetable,
while Saturday and Sunday are fully present. All three room chips appear grouped
by floor.

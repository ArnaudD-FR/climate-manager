# Lena — Student Mixed Schedule

Lena is a university student whose lecture timetable changes every day of the
week: Monday is a long day of back-to-back sessions, Tuesday has a late-morning
slot only, Wednesday is the heaviest day, Thursday is a short morning, and
Friday finishes early afternoon. Weekends she is home all day. This scenario
demonstrates how a **scheduled (single-week)** presence programme can express
genuinely varied per-weekday patterns rather than a simple repeating block.

## Household layout

| Room        | Zone         | Floor        | Heats when                        |
| ----------- | ------------ | ------------ | --------------------------------- |
| Bedroom     | Default Zone | First Floor  | Follows zone + Lena present boost |
| Study       | Default Zone | First Floor  | Follows zone + Lena present boost |
| Living Room | Default Zone | Ground Floor | Zone programme only               |

## Presence configuration

Lena uses **mode: scheduled**, **schedule_type: single**.

### Schedule

| Day | Present                    | Absent                   |
| --- | -------------------------- | ------------------------ |
| Mon | 07:00–08:00, 16:00 onwards | 00:00–07:00, 08:00–16:00 |
| Tue | 07:00–10:00, 13:00 onwards | 00:00–07:00, 10:00–13:00 |
| Wed | 07:00–08:00, 18:00 onwards | 00:00–07:00, 08:00–18:00 |
| Thu | 07:00–09:00, 12:00 onwards | 00:00–07:00, 09:00–12:00 |
| Fri | 07:00–08:00, 14:00 onwards | 00:00–07:00, 08:00–14:00 |
| Sat | all day (00:00 onwards)    | —                        |
| Sun | all day (00:00 onwards)    | —                        |

## Rooms driven by Lena

Lena's `room_ids` are **bedroom** and **study**. The living room is heated by
the zone programme but not tracked for her presence.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Bedroom     | yes                  |
| Study       | yes                  |
| Living Room | no (zone-only)       |

## Screenshots

### Overview

![Overview — Lena present, single zone](screenshots/overview.png)

The Overview shows the single Home zone active period and Lena listed as
currently present; her two linked rooms show a non-zero person count.

### Rooms

![Rooms tab — all three rooms in Default Zone](screenshots/rooms.png)

All three rooms appear under the Default Zone group with live temperature and
humidity readings, illustrating a single-zone student household.

### Persons

![Persons tab — Lena card expanded](screenshots/persons.png)

The expanded Lena card highlights the per-day time bars: each weekday row shows
a distinct pattern of absent blocks reflecting the varying class timetable,
while Saturday and Sunday are fully present. The room chips (Bedroom, Study)
appear grouped under First Floor.

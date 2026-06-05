# Emma — Simple Schedule

Emma lives alone in a two-storey house and follows a standard office week. She
leaves for work every weekday morning and returns in the late afternoon, while
weekends are entirely hers at home. This scenario shows the simplest possible
Climate Manager setup: a **single Default Zone**, four rooms, and one person on
a **scheduled (single-week)** presence programme.

## Household layout

| Room        | Zone         | Floor        | Heats when                            |
| ----------- | ------------ | ------------ | ------------------------------------- |
| Living Room | Default Zone | Ground Floor | Weekdays normal hours + full weekends |
| Kitchen     | Default Zone | Ground Floor | Weekdays normal hours + full weekends |
| Bedroom     | Default Zone | First Floor  | Follows zone + Emma present boost     |
| Home Office | Default Zone | First Floor  | Follows zone + Emma present boost     |

## Presence configuration

Emma uses **mode: scheduled**, **schedule_type: single** — the same pattern
repeats every week with no alternation.

### Schedule

| Day     | Present                  | Absent                           |
| ------- | ------------------------ | -------------------------------- |
| Mon–Fri | 07:00–09:00, 17:30–23:00 | 00:00–07:00, 09:00–17:30, 23:00+ |
| Sat–Sun | all day (00:00 onwards)  | —                                |

## Rooms driven by Emma

Emma's `room_ids` are **bedroom** and **home_office**. When she is present those
two rooms show a non-zero `present_person_count`, causing the panel to highlight
them on the Overview and in the Rooms tab.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Bedroom     | yes                  |
| Home Office | yes                  |
| Living Room | no (zone-only)       |
| Kitchen     | no (zone-only)       |

## Screenshots

### Overview

![Overview — Emma present, single zone](screenshots/overview.png)

The Overview tab shows the Default Zone (Home) active period and Emma marked as
currently present; her two linked rooms show a non-zero person count.

### Rooms

![Rooms tab — all four rooms in Default Zone](screenshots/rooms.png)

All four rooms appear under the single Default Zone group, each with live
temperature and humidity from their TRV entity.

### Persons

![Persons tab — Emma card expanded](screenshots/persons.png)

The expanded Emma card shows her single-week presence schedule: a repeating
weekday block (absent 09:00–17:30) alongside fully-present Saturday and Sunday
bars, plus the two room chips (Bedroom, Home Office) grouped by floor.

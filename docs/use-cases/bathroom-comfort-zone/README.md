# Bathrooms Comfort Zone

Bathrooms want a different heating rhythm from the rest of the house: warm for
the morning and evening wash, cooler in between, and never left cold overnight.
This example groups the two bathrooms into their own custom **Bathrooms** zone
with a `time_program` — they heat on schedule regardless of who is home. The
living areas follow the **Home** Default Zone, which is `time_program_presences`
— Alex's presence determines whether the living areas heat. This showcases the
contrast between a pure-schedule zone and a presence-driven zone side by side.

## Household layout

| Room          | Zone                    | Floor        | Heats when                       |
| ------------- | ----------------------- | ------------ | -------------------------------- |
| Main Bathroom | Bathrooms (custom zone) | First Floor  | Comfort-led schedule — always    |
| Ensuite       | Bathrooms (custom zone) | First Floor  | Comfort-led schedule — always    |
| Living Room   | Home (Default Zone)     | Ground Floor | Domestic schedule — Alex present |
| Bedroom       | Home (Default Zone)     | First Floor  | Domestic schedule — Alex present |

Both bathrooms are assigned to the **Bathrooms** zone via `zone_id`. They need
no assigned person because the Bathrooms zone uses `time_program` — rooms in a
`time_program` zone heat according to their zone's schedule regardless of
presence. The living areas stay in the Default Zone (presences) and need Alex
assigned so the schedule applies when he is home.

## Zone modes compared

| Zone        | Mode                     | Person needed | Heats when                        |
| ----------- | ------------------------ | ------------- | --------------------------------- |
| Bathrooms   | `time_program`           | No            | Schedule runs at all times        |
| Home (Def.) | `time_program_presences` | Yes (Alex)    | Schedule runs only when Alex home |

The key distinction: a `time_program` zone ignores presence entirely. A
`time_program_presences` zone only applies the schedule when at least one
assigned person is present; otherwise the room sets back to Reduced.

## Zone programs compared

### Bathrooms zone — weekdays (Mon–Fri)

| From  | Period                |
| ----- | --------------------- |
| 00:00 | Frost protection      |
| 06:30 | **Comfort** (wake-up) |
| 08:30 | **Reduced** (daytime) |
| 19:00 | **Comfort** (evening) |
| 22:00 | Frost protection      |

### Bathrooms zone — weekend (Sat–Sun)

| From  | Period                      |
| ----- | --------------------------- |
| 00:00 | Frost protection            |
| 08:00 | **Comfort** (later wake-up) |
| 10:00 | **Normal** (daytime)        |
| 19:00 | **Comfort** (evening)       |
| 23:00 | Frost protection            |

The bathrooms are at comfort for the morning and evening wash, reduced during
the working day (normal at weekends), and never warmer than needed overnight —
independent of whether anyone is home.

## Occupant

Alex (`mode: 'scheduled'`) is assigned to **bedroom** and **living_room** only.
His presence gates the Home zone schedule for those two rooms. The bathrooms
heat purely from their Bathrooms zone program — they do not depend on Alex's
presence, which is exactly why `time_program` (not `time_program_presences`) is
the right zone mode for them.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

The Overview lists both zones — **Home** in its normal evening period
(presence-driven, Alex is present) and **Bathrooms** showing its **comfort**
active period (schedule-driven, no presence required).

### Rooms tab

![Rooms](screenshots/rooms.png)

The expanded Main Bathroom card carries the **Bathrooms** zone badge and its
comfort-period temperature, with `present_person_count: 0` — comfort runs
regardless. The Living Room and Bedroom cards sit in the Home zone with Alex's
presence count of 1.

### Persons tab — Alex card expanded

![Persons](screenshots/persons.png)

Alex's card shows a simple single-week schedule with Bedroom and Living Room
chips — confirming the bathrooms' comfort schedule is driven by the zone, not by
presence.

# Bathrooms Comfort Zone

Bathrooms want a different heating rhythm from the rest of the house: warm for
the morning and evening wash, cooler in between, and never left cold overnight.
This example groups the two bathrooms into their own custom **Bathrooms** zone
with mode **Time program** — they heat on schedule regardless of who is home.
The living areas follow the **Home** Default Zone, which is **Time program &
presences** — Alex's presence determines whether the living areas heat. This
showcases the contrast between a pure-schedule zone and a presence-driven zone
side by side.

## Household layout

| Room          | Zone                    | Floor        | Heats when                       |
| ------------- | ----------------------- | ------------ | -------------------------------- |
| Main Bathroom | Bathrooms (custom zone) | First Floor  | Comfort-led schedule — always    |
| Ensuite       | Bathrooms (custom zone) | First Floor  | Comfort-led schedule — always    |
| Living Room   | Home (Default Zone)     | Ground Floor | Domestic schedule — Alex present |
| Bedroom       | Home (Default Zone)     | First Floor  | Domestic schedule — Alex present |

Both bathrooms are assigned to the **Bathrooms** zone via the **Zone** selector.
They need no assigned person because the Bathrooms zone uses **Time program** —
rooms in a **Time program** zone heat according to their zone's schedule
regardless of presence. The living areas stay in the Default Zone and need Alex
assigned so the schedule applies when he is home.

## Zone modes compared

| Zone        | Mode                     | Person needed | Heats when                        |
| ----------- | ------------------------ | ------------- | --------------------------------- |
| Bathrooms   | Time program             | No            | Schedule runs at all times        |
| Home (Def.) | Time program & presences | Yes (Alex)    | Schedule runs only when Alex home |

The key distinction: a **Time program** zone ignores presence entirely. A **Time
program & presences** zone only applies the schedule when at least one assigned
person is present; otherwise the room sets back to Reduced.

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

The bathrooms are at Comfort for the morning and evening wash, Reduced during
the working day (Normal at weekends), and never warmer than needed overnight —
independent of whether anyone is home.

## Occupant

Alex uses **Scheduled** presence mode (single week) and is assigned to
**Bedroom** and **Living Room** only via his **Room associations**. His presence
gates the Home zone schedule for those two rooms. The bathrooms heat purely from
their Bathrooms zone program — they do not depend on Alex's presence, which is
exactly why **Time program** (not **Time program & presences**) is the right
zone mode for them.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

Captured at 20:00 on a Wednesday evening: Home zone is in its Normal active
period (**Time program & presences**, Alex is present) and Bathrooms zone is in
**Comfort** (**Time program**, schedule-driven regardless of presence). Alex
appears in the Persons row with a green dot.

### Rooms tab

![Rooms](screenshots/rooms.png)

First Floor shows Bedroom (Normal · 20°C, Home, 1/1 with Alex), Ensuite (Comfort
· 22°C, Bathrooms, 0 persons), and Main Bathroom (Comfort · 22°C, Bathrooms, 0
persons). Ground Floor shows Living Room (Normal · 20°C, Home, 1/1). The
expanded Bedroom card shows Alex in Associated Persons and the Bedroom TRV at
19.4°C. The two bathroom cards have 0 in their person count — Comfort runs
regardless.

### Persons tab — Alex card expanded

![Persons](screenshots/persons.png)

Alex's card shows a **Single week** schedule: present overnight and in the
evening, absent 08:30–18:00 on weekdays, present all weekend. Room associations
list Bedroom (First Floor) and Living Room (Ground Floor) — confirming the
bathrooms' Comfort schedule is driven by the zone, not by Alex's presence.

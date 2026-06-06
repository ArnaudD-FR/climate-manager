# Marc — Rotating Shift Worker

Marc works irregular rotating shifts at a factory — early mornings one week,
late nights the next. His home presence follows no predictable weekly pattern,
so a fixed time-bar schedule would constantly be wrong. Instead the integration
tracks Marc's HA person entity using **HA home tracking**, which follows his
home/away state directly. Rooms heat while he is home and set back to Reduced
when he leaves — no schedule editor needed.

## Household layout

| Room        | Zone                      | Floor        | Heats when   |
| ----------- | ------------------------- | ------------ | ------------ |
| Bedroom     | Upstairs (custom zone)    | First Floor  | Marc is home |
| Living Room | Downstairs (Default Zone) | Ground Floor | Marc is home |
| Kitchen     | Downstairs (Default Zone) | Ground Floor | Marc is home |

Both zones use **Time program & presences** mode. Rooms heat to their zone's
time-program schedule while Marc is home; when he leaves all rooms fall back to
Reduced regardless of the scheduled period.

## Presence configuration

Marc's person config uses **HA home tracking**. No schedule arrays are needed.
The integration reads his HA person entity's home / away state at each
evaluation cycle, derived from his phone's device tracker. The hint on his card
reads "Presence mirrors Home Assistant home/away tracking."

The panel renders the **HA home tracking** badge on Marc's card. This mode is
the right choice for anyone whose schedule is irregular enough that no weekly
repeat pattern is practical — shift workers, on-call staff, or people with
highly variable routines. The person card shows no schedule editor.

## Rooms driven by Marc

Marc has all three rooms in his **Room associations**: Bedroom (First Floor) and
Kitchen + Living Room (Ground Floor). Every room is gated by his presence —
heating follows the zone schedule while he is home and sets back when he is
away.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Bedroom     | yes                  |
| Living Room | yes                  |
| Kitchen     | yes                  |

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

Captured at 14:00 on a Wednesday: Marc is home (green dot in the Persons row),
Downstairs zone is in its Normal active period and Upstairs in Reduced — both
zones show **Time program & presences** mode.

### Rooms tab

![Rooms](screenshots/rooms.png)

All three rooms show 1/1 person present. Bedroom (First Floor) carries the
Upstairs zone badge and a Normal · 20°C period; Kitchen and Living Room (Ground
Floor) carry the Downstairs badge, also at Normal · 20°C. The expanded Bedroom
card shows Marc in Associated Persons and the Bedroom TRV reading 19.2°C.

### Persons tab — Marc card expanded

![Persons](screenshots/persons.png)

The expanded Marc card shows the Presence mode selector set to **HA home
tracking** and the hint "Presence mirrors Home Assistant home/away tracking." No
schedule editor is rendered — this is the deliberate contrast with
schedule-driven cards, where a time-bar editor appears on expand. Room
associations list Bedroom (First Floor) and Kitchen + Living Room (Ground
Floor).

### Zone schedules

Both floors run in **Time program & presences** mode, so each zone's weekly
schedule bounds heating; Marc's HA home tracking presence only gates it.

![Downstairs zone schedule](screenshots/schedule-downstairs.png)

**Downstairs** heats Normal 07:00–09:30, Reduced through midday, Normal
18:00–22:30 on weekdays, with a Normal/Comfort weekend block 08:30–23:00.

![Upstairs zone schedule](screenshots/schedule-upstairs.png)

**Upstairs** heats Normal 06:30–09:00 and 17:00–22:00 on weekdays,
Normal/Comfort 08:00–23:00 at weekends. Whichever shift Marc is on, neither
floor heats outside these windows — the schedule, not his home/away state, sets
the outer bounds.

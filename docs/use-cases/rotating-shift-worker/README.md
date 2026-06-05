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
The integration reads his HA person entity's home / not_home state at each
evaluation cycle, derived from his phone's device tracker.

The panel renders the **HA home tracking** badge on Marc's card. This mode is
the right choice for anyone whose schedule is irregular enough that no weekly
repeat pattern is practical — shift workers, on-call staff, or people with
highly variable routines. The person card shows no schedule editor.

## Rooms driven by Marc

Marc has all three rooms in his **Room associations**: Bedroom, Living Room, and
Kitchen. Every room is gated by his presence — heating follows the zone schedule
while he is home and sets back when he is away.

| Room        | Tracked for presence |
| ----------- | -------------------- |
| Bedroom     | yes                  |
| Living Room | yes                  |
| Kitchen     | yes                  |

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

The Overview tab shows the two zones (Downstairs and Upstairs), both in **Time
program & presences** mode, and Marc's presence state. All three rooms show a
non-zero person count while he is home.

### Rooms tab

![Rooms](screenshots/rooms.png)

The Rooms tab lists all three rooms grouped by floor. Bedroom is badged with the
Upstairs zone colour; Living Room and Kitchen show the Downstairs (Default Zone)
badge. Each card shows live temperature and humidity from the TRV.

### Persons tab — Marc card expanded

![Persons](screenshots/persons.png)

The expanded Marc card shows the Presence mode selector set to **HA home
tracking** and an explanatory hint. No schedule editor is rendered — this is the
deliberate contrast with schedule-driven cards (e.g. simple-schedule or
student-mixed-schedule), where a time-bar editor appears on expand. All three
room chips appear in his **Room associations**, grouped by floor.

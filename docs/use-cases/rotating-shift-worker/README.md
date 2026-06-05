# Marc — Rotating Shift Worker

Marc works irregular rotating shifts at a factory — early mornings one week,
late nights the next. His home presence follows no predictable weekly pattern,
so a fixed time-bar schedule would constantly be wrong. Instead the integration
tracks the live `person.marc` HA entity, which is updated in real time by his
phone's device tracker.

## Household layout

| Room        | Zone                      | Floor        | Heats when                      |
| ----------- | ------------------------- | ------------ | ------------------------------- |
| Bedroom     | Upstairs (custom zone)    | First Floor  | Marc is home (presence-driven)  |
| Living Room | Downstairs (Default Zone) | Ground Floor | Time program (always scheduled) |
| Kitchen     | Downstairs (Default Zone) | Ground Floor | Time program (always scheduled) |

The **Downstairs** Default Zone runs a fixed time program: warm mornings and
evenings, reduced during the day. The **Upstairs** custom zone uses
`time_program_presences` mode — it heats on the same base schedule but only when
at least one tracked person is present.

## Presence configuration

Marc's person config uses `mode: 'ha'`. No schedule arrays are stored. The
integration reads `person.marc`'s `home` / `not_home` state from HA at each
evaluation cycle, which in turn is derived from `device_tracker.marc_phone`.

Because `device_trackers` is set to a non-empty list in HA's person entity
attributes, the panel renders the clean **HA** badge on Marc's card. If the
tracker list were empty the card would show a warning badge instead.

This mode is the right choice for anyone whose schedule is irregular enough that
no weekly repeat pattern is practical — shift workers, on-call staff, or people
with highly variable routines.

## Rooms driven by Marc

Marc's `room_ids: ['bedroom']` means only the Bedroom reacts to his presence.
When he arrives home the Upstairs zone activates heating in the Bedroom. Living
Room and Kitchen follow their own time program regardless.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

The Overview tab shows the two zones (Downstairs and Upstairs), their current
modes, and Marc's presence state. The Upstairs zone badge reflects the
`time_program_presences` mode.

### Rooms tab

![Rooms](screenshots/rooms.png)

The Rooms tab lists all three rooms grouped by floor. Bedroom is badged with the
Upstairs zone colour; Living Room and Kitchen show the Default Zone (Downstairs)
badge. Each card shows live temperature and humidity from the TRV.

### Persons tab — Marc card expanded

![Persons](screenshots/persons.png)

The expanded Marc card shows the mode selector set to **HA** and an explanatory
hint. No schedule editor is rendered — this is the deliberate contrast with
schedule-driven cards (e.g. simple-schedule or student-mixed-schedule), where a
time-bar editor appears on expand. The room chip shows Bedroom grouped under
First Floor.

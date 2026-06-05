# Maya — Predictive Pre-heat

Maya wants her bedroom and bathroom to be warm when she wakes up, not to _start_
heating when she gets out of bed. With **pre-heat** enabled on the Home zone,
the coordinator looks ahead to the 06:30 Normal period and begins heating early
— using each room's allowed lead time — so the rooms reach target temperature
right as the morning period begins. Maya is home asleep overnight and that
counts as **present**, so pre-heat can run ahead of the wake-up step.

## Household layout

| Room        | Zone                | Floor        | Heats when                             |
| ----------- | ------------------- | ------------ | -------------------------------------- |
| Bedroom     | Home (Default Zone) | First Floor  | Time program + pre-heat before wake-up |
| Bathroom    | Home (Default Zone) | First Floor  | Time program + pre-heat before wake-up |
| Living Room | Home (Default Zone) | Ground Floor | Time program (no pre-heat lead)        |

The Default Zone **Home** uses `time_program_presences` and has
`preheat_enabled: true`. A room must have an assigned person in a presences zone
to be pre-heated; a room with no assigned person would be set back, not
pre-heated.

## Presence configuration

Maya uses `mode: 'scheduled'` (single week).

| Day       | Present                              | Away          |
| --------- | ------------------------------------ | ------------- |
| Mon–Fri   | Overnight, before 08:30, after 17:30 | 08:30 – 17:30 |
| Sat / Sun | All day                              | —             |

Asleep at home overnight is **present** — absence is only for the hours Maya is
actually out of the house. Pre-heat fires at ~05:50 on weekday mornings (up to
60–90 minutes ahead of 06:30) while Maya is home asleep.

Pre-heat tuning:

- **`preheat_max_lead_minutes`** per room — Bedroom 60 min, Bathroom 90 min: the
  maximum head-start the coordinator may take for that room ahead of the next
  warmer period.
- Pre-heat is driven by the zone `preheat_enabled` flag and per-room lead time.
  There is no `wakeup_advance_minutes` on Maya's config — that knob is for
  calendar-mode persons only.

## Rooms driven by Maya

`room_ids: ['bedroom', 'bathroom', 'living_room']` — all three rooms are in the
Home zone (`time_program_presences`), so each must have an assigned person or it
would never heat to its scheduled period. The Living Room has no
`preheat_max_lead_minutes`, so it starts heating only when the 06:30 period
arrives; it does not get an early start.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

Captured at ~05:50 on a weekday morning: Maya is home asleep (present), the
system is already pre-heating the bedroom and bathroom toward the 06:30 Normal
step.

### Rooms tab

![Rooms](screenshots/rooms.png)

The expanded Bedroom card shows the **Pre-heating → 20.0 °C** badge and its
60-minute max lead setting. The Bathroom card likewise shows pre-heat active
with its 90-minute lead. The Living Room card is in the overnight reduced period
with no pre-heat badge.

### Persons tab — Maya card expanded

![Persons](screenshots/persons.png)

Maya's card shows her weekday schedule, and her three room chips — Bedroom,
Bathroom (First Floor), and Living Room (Ground Floor) — the rooms her presence
gates in the Home zone.

# Maya — Predictive Pre-heat

Maya works standard office hours and wants her home to be warm the moment she
walks in, not to _start_ heating when she arrives. With **pre-heat** enabled on
her zone, the coordinator looks ahead to her scheduled return and begins heating
early — using each room's allowed lead time — so the rooms reach target
temperature right as she gets home.

## Household layout

| Room        | Zone                | Floor        | Heats when                              |
| ----------- | ------------------- | ------------ | --------------------------------------- |
| Living Room | Home (Default Zone) | Ground Floor | Time program + pre-heat before Maya     |
| Bedroom     | Home (Default Zone) | First Floor  | Time program + pre-heat before Maya     |
| Bathroom    | Home (Default Zone) | First Floor  | Time program only (pre-heat suppressed) |

The Default Zone **Home** uses `time_program_presences` and has
`preheat_enabled: true`, so any room driven by a person's schedule can be
pre-heated ahead of their return.

## Presence configuration

Maya uses `mode: 'scheduled'` (single week). Her schedule gives the coordinator
the predicted arrival that pre-heat plans against.

| Day       | Present                              | Away          |
| --------- | ------------------------------------ | ------------- |
| Mon–Fri   | Overnight, before 08:30, after 17:30 | 08:30 – 17:30 |
| Sat / Sun | All day                              | —             |

Pre-heat tuning:

- **`wakeup_advance_minutes: 45`** on Maya — start heating up to 45 minutes
  before her predicted 17:30 return.
- **`preheat_max_lead_minutes`** per room — Living Room 90 min, Bedroom 120 min:
  the maximum head-start the coordinator may take for that room.

## Rooms driven by Maya

`room_ids: ['living_room', 'bedroom']` — only these two rooms react to Maya's
presence and are pre-heated for her arrival. The **Bathroom** has no person
assigned, so even though the zone enables pre-heat the bathroom shows
`preheat_suppressed` — there is no schedule to predict, so it simply follows the
time program.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

Captured late on a weekday afternoon: Maya is still out (no one present) while
the system is already pre-heating toward her return.

### Rooms tab

![Rooms](screenshots/rooms.png)

The expanded Living Room card shows the **Pre-heating → 20.0 °C** badge and the
pre-heat section with its max-lead setting. The Bathroom card shows the
suppressed state (pre-heat enabled on the zone but no schedule to act on).

### Persons tab — Maya card expanded

![Persons](screenshots/persons.png)

Maya's card shows her weekday schedule, the **pre-heat advance** field (45
minutes), and her room chips — Living Room (Ground Floor) and Bedroom (First
Floor) — the rooms her presence pre-heats.

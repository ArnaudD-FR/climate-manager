# Sofia — Shared Custody (Odd/Even Weeks)

Sofia is a child who alternates between two homes under a shared-custody
arrangement: she is present every other week and away the alternate weeks. The
hand-over happens cleanly at week boundaries (ISO week numbering). This example
shows how the **scheduled even/odd weeks** presence mode automates heating for
exactly that pattern — no manual intervention required when the week flips.

## Household layout

| Room            | Zone                       | Floor        | Heats when                      |
| --------------- | -------------------------- | ------------ | ------------------------------- |
| Child's Bedroom | Child's Room (custom zone) | First Floor  | Sofia present (even weeks)      |
| Living Room     | Home (Default Zone)        | Ground Floor | Time program (always scheduled) |

The **Home** Default Zone runs a standard time program for the living room. The
**Child's Room** custom zone uses `time_program_presences` mode — it heats
according to its own schedule only when Sofia is marked present by the even/odd
programme.

## Presence configuration

Sofia's config uses `mode: 'scheduled'` with `schedule_type: 'even_odd'`. Two
independent weekly programmes are stored:

### Schedule (even / odd weeks)

| Week parity | Mon             | Tue     | Wed     | Thu     | Fri     | Sat     | Sun     |
| ----------- | --------------- | ------- | ------- | ------- | ------- | ------- | ------- |
| Even week   | Present all day | Present | Present | Present | Present | Present | Present |
| Odd week    | Absent all day  | Absent  | Absent  | Absent  | Absent  | Absent  | Absent  |

Each day has a single period starting at `00:00` — either fully present or fully
absent. The integration's coordinator reads the current ISO week number at each
evaluation cycle and applies the matching schedule.

**Note on screenshots:** The panel computes the active week parity from the real
system clock at capture time (`getWeekParity(new Date())`). The persons
screenshot will show whichever week tab is currently active. Both tabs (Even and
Odd) exist on the card and can be toggled by the user in the live UI.

## Rooms driven by Sofia

Sofia's `room_ids: ['child_bedroom', 'living_room']` means both rooms react to
her presence. On even weeks (present) the Child's Bedroom heats normally; on odd
weeks (absent) it falls back to frost protection. The Living Room also follows
her presence for its comfort-mode boost periods.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

The Overview tab shows the two zones (Home and Child's Room) with their current
modes. The Child's Room zone badge reflects `time_program_presences`. Sofia's
presence state is shown as present (even-week capture).

### Rooms tab

![Rooms](screenshots/rooms.png)

The Rooms tab lists Child's Bedroom (First Floor, Child's Room zone badge) and
Living Room (Ground Floor, Default Zone badge). Temperature and humidity
readings are shown for each TRV.

### Persons tab — Sofia card expanded

![Persons](screenshots/persons.png)

The expanded Sofia card shows the **Even / Odd** week-switcher tabs and the
schedule bars for the active week. The screenshot reflects whichever parity is
current at capture time. The Even tab shows all-present bars; the Odd tab shows
all-absent bars. Room chips list Child's Bedroom (First Floor) and Living Room
(Ground Floor), demonstrating the multi-floor room association.

# Sofia — Shared Custody (Odd/Even Weeks)

Sofia is a child who alternates between two homes under a shared-custody
arrangement. The hand-over happens **every Friday at noon**, so one week she is
here for the school days and leaves for the weekend, and the alternate week she
arrives for the weekend and is away during the school days. This example shows
how the **Even / Odd weeks** presence schedule combines with a **per-day
Calendar** source and a **manual weekend schedule** in a single person config —
automating a genuinely mixed custody pattern with no manual intervention when
the week flips.

## Household layout

| Room            | Zone                       | Floor        | Heats when                       |
| --------------- | -------------------------- | ------------ | -------------------------------- |
| Child's Bedroom | Child's Room (custom zone) | First Floor  | Sofia present (per the schedule) |
| Living Room     | Home (Default Zone)        | Ground Floor | Time program (always scheduled)  |

The **Home** Default Zone runs a standard time program for the living room. The
**Child's Room** custom zone uses **Time program & presences** mode — it heats
according to its own schedule only when Sofia is marked present.

## Presence configuration

Sofia's presence mode is **Scheduled** with an **Even / Odd weeks** schedule,
but each week's program is itself **mixed**: weekdays are driven by the
**Pronote — Collège** Calendar source (each day's period is set to **Calendar**
and watches that calendar) and the weekend is a **hand-set manual** schedule.
The custody hand-over at **Friday noon** means Friday is split at 12:00 in both
programs.

### Odd week — here for the school week, leaves Friday noon

| Mon–Thu          | Fri                          | Sat    | Sun    |
| ---------------- | ---------------------------- | ------ | ------ |
| Pronote calendar | Pronote until 12:00 → absent | Absent | Absent |

On school days, the Pronote — Collège timetable drives presence: while a class
event is active the child is at school (absent); after school she is home. The
Calendar source is set to **Absent during events** and short gaps between
classes do not count as home — only a gap longer than 60 minutes triggers a
return home.

### Even week — arrives Friday noon, manual weekend

| Mon–Thu | Fri                          | Sat (manual)                         | Sun (manual)                         |
| ------- | ---------------------------- | ------------------------------------ | ------------------------------------ |
| Absent  | Absent until 12:00 → present | Present, out 14:00–18:00, back 18:00 | Present, out 14:00–18:00, back 18:00 |

The weekend days use hand-set present/absent periods (e.g. an afternoon out),
which read as plain manual bars rather than Calendar bars.

**Parity at capture:** The scenario is pinned to Wednesday 16:30 UTC, ISO week
23 (odd week). The Persons screenshot shows the **Odd** tab active; both Even
and Odd tabs exist on the card and can be toggled in the live UI.

## Rooms driven by Sofia

Sofia is assigned to the **Child's Bedroom** only (via **Room associations**).
That room is in the presence-driven **Child's Room** zone, so it follows the
schedule when she is marked present and falls back to Reduced when she is
absent. The **Living Room** is in the **Home** zone on a plain time program — it
is a shared family space that heats on schedule regardless of who is home, so it
needs no person assigned.

## Screenshots

### Overview tab

![Overview](screenshots/overview.png)

Captured at 16:30 on a Wednesday (odd week, ISO 23): Home zone is in Reduced
(**Time program**) and Child's Room zone is in Normal (**Time program &
presences**). Sofia is present (green dot), having returned home after school.

### Rooms tab

![Rooms](screenshots/rooms.png)

Child's Bedroom (First Floor) shows a Normal · 20°C badge with the Child's Room
zone chip and 1/1 person present; the expanded card shows Sofia in Associated
Persons and the TRV reading 18.8°C. Living Room (Ground Floor) shows Reduced ·
16°C with the Home zone badge and 0 persons — it heats on its own schedule with
no presence gate.

### Persons tab — Sofia card expanded

![Persons](screenshots/persons.png)

The expanded Sofia card shows the **Even / Odd weeks** selector with the note
"Week 23 is currently active (odd week)." The **Odd** tab is active, showing
Mon–Thu as Calendar: pronote bars (all-day), Friday split with Calendar: pronote
until noon and Absent from noon, then Absent on Saturday and Sunday. Below the
schedule, the Calendar config panel displays the **Pronote — Collège** source
for Mon's Calendar period. The room chip lists Child's Bedroom (First Floor) —
the only presence-gated room Sofia drives.

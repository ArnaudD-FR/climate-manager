# Marc — Rotating Shift Worker

Marc works irregular rotating shifts, so his home presence cannot be predicted
by a fixed weekly schedule. This example shows how to use the **HA tracking**
presence mode, where the integration follows the Home Assistant `person`
entity's live home/away state rather than a time-based program.

## Configuration Summary

| Property       | Value                                                 |
| -------------- | ----------------------------------------------------- |
| Presence mode  | `ha` / live tracking                                  |
| Schedule shape | None — follows the HA person entity's home/away state |
| Assigned rooms | Bedroom                                               |

## Screenshots

### Persons tab — Marc card expanded

![Marc person card expanded](screenshots/persons.png)

The expanded card shows the mode selector and a hint explaining that presence is
driven by the HA person entity. No schedule editor is displayed — this is the
deliberate contrast with schedule-driven personas such as the simple-schedule or
student-mixed-schedule use cases, where a time-bar editor appears on expand.

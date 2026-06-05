# Noah — Business Calendar

Noah's presence at home is driven by his work calendar: whenever a meeting or
travel event appears in his calendar, he is away. This example shows how to use
the **calendar** presence mode to delegate scheduling to a `calendar.*` entity.

## Configuration Summary

The table below is the Configuration Summary for this use case.

| Property        | Value                                             |
| --------------- | ------------------------------------------------- |
| Presence mode   | `calendar`                                        |
| Source          | `calendar.work_meetings` — events mean away       |
| Gap handling    | `day_span` — absent for the whole day of an event |
| Wake-up advance | 60 minutes (pre-heat before return)               |
| Assigned rooms  | Office, Bedroom                                   |

## Screenshots

### Persons tab — Noah card expanded

![Noah person card expanded](screenshots/persons.png)

The expanded card shows the calendar config selectors (entity, event meaning,
gap handling, and wake-up advance); no schedule time-bar editor is shown because
calendar mode delegates presence to the linked entity.
